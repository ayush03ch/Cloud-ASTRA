# agents/ec2_agent/rules/unencrypted_ebs_rule.py

import boto3
from botocore.exceptions import ClientError


class UnencryptedEBSRule:
    """
    Rule to detect EC2 instances with unencrypted EBS volumes.
    """
    
    id = "ec2_unencrypted_ebs"
    detection = "EC2 instance has unencrypted EBS volumes"
    auto_safe = False  # Encryption requires instance restart
    
    def __init__(self):
        self.fix_instructions = None
        self.can_auto_fix = False
        self.fix_type = None
        self.unencrypted_volumes = None
    
    def check(self, client, instance_id):
        """Check for unencrypted EBS volumes."""
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
            
            # Check encryption status of volumes
            volumes_response = client.describe_volumes(VolumeIds=volume_ids)
            unencrypted_volumes = []
            
            for volume in volumes_response['Volumes']:
                if not volume.get('Encrypted', False):
                    unencrypted_volumes.append({
                        'volume_id': volume['VolumeId'],
                        'size': volume['Size'],
                        'type': volume['VolumeType'],
                        'device': self._get_device_name(instance, volume['VolumeId']),
                        'state': volume['State']
                    })
            
            if unencrypted_volumes:
                self.unencrypted_volumes = unencrypted_volumes
                self._set_fix_instructions(unencrypted_volumes, instance_id)
                print(f"🔴 Found {len(unencrypted_volumes)} unencrypted EBS volumes for {instance_id}")
                return True
            
            return False
            
        except ClientError as e:
            print(f"❌ Error checking EBS encryption for {instance_id}: {e}")
            return False
    
    def _get_device_name(self, instance, volume_id):
        """Get device name for volume."""
        for bdm in instance.get('BlockDeviceMappings', []):
            if bdm.get('Ebs', {}).get('VolumeId') == volume_id:
                return bdm.get('DeviceName', 'Unknown')
        return 'Unknown'
    
    def _set_fix_instructions(self, unencrypted_volumes, instance_id):
        """Set instructions for encrypting EBS volumes."""
        total_size = sum(vol['size'] for vol in unencrypted_volumes)
        
        self.fix_instructions = [
            f"🔐 Unencrypted EBS Volumes for {instance_id}",
            f"Found {len(unencrypted_volumes)} unencrypted volumes ({total_size} GB total):"
        ]
        
        for vol in unencrypted_volumes:
            self.fix_instructions.extend([
                f"• Volume ID: {vol['volume_id']}",
                f"  Device: {vol['device']}, Size: {vol['size']} GB, Type: {vol['type']}",
                f"  State: {vol['state']}"
            ])
        
        self.fix_instructions.extend([
            "🔧 Encryption Process:",
            "1. Create encrypted snapshot of unencrypted volume",
            "2. Create new encrypted volume from encrypted snapshot",
            "3. Stop the EC2 instance",
            "4. Detach original volume and attach encrypted volume",
            "5. Update device mapping if necessary", 
            "6. Start instance and verify functionality",
            "💡 Alternative: Enable encryption by default for new volumes",
            "1. Go to EC2 > Settings > EBS encryption",
            "2. Enable 'Always encrypt new EBS volumes'",
            "⚠️ Impact: Instance downtime required for encryption"
        ])
        
        self.can_auto_fix = False  # Requires downtime
        self.fix_type = "encrypt_ebs_volumes"
    
    def fix(self, client, instance_id):
        """Fix unencrypted EBS volumes - requires manual process."""
        return {
            "success": False,
            "message": "EBS encryption requires instance downtime and manual process",
            "unencrypted_volumes": len(self.unencrypted_volumes) if self.unencrypted_volumes else 0,
            "recommendation": "Follow the encryption process in fix instructions"
        }
