# agents/ec2_agent/rules/missing_backups_rule.py

import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta


class MissingBackupsRule:
    """
    Rule to detect EC2 instances without recent EBS snapshots (backups).
    """
    
    id = "ec2_missing_backups"
    detection = "EC2 instance has no recent EBS snapshots"
    auto_safe = True  # Safe to create snapshots
    
    def __init__(self):
        self.fix_instructions = None
        self.can_auto_fix = True
        self.fix_type = None
        self.volumes_without_backups = None
        self.backup_threshold_days = 7
    
    def check(self, client, instance_id, backup_days_threshold=7):
        """Check for missing EBS snapshots."""
        self.backup_threshold_days = backup_days_threshold
        
        try:
            # Get instance details
            response = client.describe_instances(InstanceIds=[instance_id])
            if not response['Reservations']:
                return False
            
            instance = response['Reservations'][0]['Instances'][0]
            
            # Get EBS volume IDs
            volume_ids = []
            for bdm in instance.get('BlockDeviceMappings', []):
                if 'Ebs' in bdm:
                    volume_ids.append(bdm['Ebs']['VolumeId'])
            
            if not volume_ids:
                return False
            
            volumes_without_backups = []
            
            for volume_id in volume_ids:
                # Check for recent snapshots
                snapshots = client.describe_snapshots(
                    Filters=[
                        {'Name': 'volume-id', 'Values': [volume_id]},
                        {'Name': 'status', 'Values': ['completed']}
                    ],
                    OwnerIds=['self']
                )
                
                # Check if there are any recent snapshots
                recent_snapshots = []
                threshold_date = datetime.utcnow() - timedelta(days=backup_days_threshold)
                
                for snapshot in snapshots['Snapshots']:
                    start_time = snapshot['StartTime'].replace(tzinfo=None)
                    if start_time > threshold_date:
                        recent_snapshots.append(snapshot)
                
                if not recent_snapshots:
                    # Get volume details
                    volumes = client.describe_volumes(VolumeIds=[volume_id])
                    if volumes['Volumes']:
                        volume = volumes['Volumes'][0]
                        volumes_without_backups.append({
                            'volume_id': volume_id,
                            'size': volume['Size'],
                            'type': volume['VolumeType'],
                            'device': self._get_device_name(instance, volume_id),
                            'last_snapshot': self._get_last_snapshot_date(snapshots['Snapshots']),
                            'total_snapshots': len(snapshots['Snapshots'])
                        })
            
            if volumes_without_backups:
                self.volumes_without_backups = volumes_without_backups
                self._set_fix_instructions(volumes_without_backups, instance_id)
                print(f"🔴 Found {len(volumes_without_backups)} volumes without recent backups for {instance_id}")
                return True
            
            return False
            
        except ClientError as e:
            print(f"❌ Error checking backups for {instance_id}: {e}")
            return False
    
    def _get_device_name(self, instance, volume_id):
        """Get device name for volume."""
        for bdm in instance.get('BlockDeviceMappings', []):
            if bdm.get('Ebs', {}).get('VolumeId') == volume_id:
                return bdm.get('DeviceName', 'Unknown')
        return 'Unknown'
    
    def _get_last_snapshot_date(self, snapshots):
        """Get the date of the most recent snapshot."""
        if not snapshots:
            return None
        
        latest = max(snapshots, key=lambda s: s['StartTime'])
        return latest['StartTime'].strftime('%Y-%m-%d')
    
    def _set_fix_instructions(self, volumes_without_backups, instance_id):
        """Set instructions for creating backups."""
        total_size = sum(vol['size'] for vol in volumes_without_backups)
        
        self.fix_instructions = [
            f"💾 Missing Backups for {instance_id}",
            f"Found {len(volumes_without_backups)} volumes without recent backups ({total_size} GB total):",
            ""
        ]
        
        for vol in volumes_without_backups:
            last_backup = vol['last_snapshot'] if vol['last_snapshot'] else 'Never'
            self.fix_instructions.extend([
                f"• Volume ID: {vol['volume_id']}",
                f"  Device: {vol['device']}, Size: {vol['size']} GB",
                f"  Last backup: {last_backup} ({vol['total_snapshots']} total snapshots)",
                ""
            ])
        
        self.fix_instructions.extend([
            "🔧 Backup Setup:",
            "1. Create immediate manual snapshot for each volume",
            "2. Set up Data Lifecycle Manager (DLM) for automated snapshots",
            "3. Configure retention policy (e.g., daily for 7 days, weekly for 4 weeks)",
            "4. Add tags for easier snapshot management",
            "",
            "💡 Alternative: Use AWS Backup for comprehensive backup strategy",
            "1. Go to AWS Backup console",
            "2. Create backup plan with appropriate schedule",
            "3. Assign EC2 instances to backup plan",
            "",
            "💰 Cost: Snapshots are charged for incremental storage used"
        ])
        
        self.can_auto_fix = True  # Safe to create snapshots
        self.fix_type = "create_ebs_snapshots"
    
    def fix(self, client, instance_id):
        """Create EBS snapshots for volumes without backups."""
        try:
            if not self.volumes_without_backups:
                return {"success": False, "message": "No volumes to backup"}
            
            created_snapshots = []
            errors = []
            
            for volume in self.volumes_without_backups:
                try:
                    # Create snapshot
                    response = client.create_snapshot(
                        VolumeId=volume['volume_id'],
                        Description=f"Backup snapshot for {instance_id} {volume['device']} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
                    )
                    
                    created_snapshots.append({
                        'volume_id': volume['volume_id'],
                        'snapshot_id': response['SnapshotId'],
                        'device': volume['device'],
                        'size': volume['size']
                    })
                    
                    print(f"✅ Created snapshot {response['SnapshotId']} for volume {volume['volume_id']}")
                    
                except ClientError as e:
                    error_msg = f"Failed to create snapshot for volume {volume['volume_id']}: {e}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
            
            return {
                "success": len(created_snapshots) > 0,
                "message": f"Created {len(created_snapshots)} snapshots",
                "created_snapshots": created_snapshots,
                "errors": errors,
                "next_steps": [
                    "Set up Data Lifecycle Manager for automated backups",
                    "Monitor snapshot completion status",
                    "Configure backup retention policies"
                ]
            }
            
        except ClientError as e:
            return {
                "success": False,
                "message": f"Error creating snapshots: {e}",
                "recommendation": "Manual snapshot creation required"
            }
