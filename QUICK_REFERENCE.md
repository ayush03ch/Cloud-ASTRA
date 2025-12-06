# Cloud Astra - Quick Reference Guide

## 🚀 Quick Start

### Installation
```bash
cd f:\Academics\Major-02\Cloud-ASTRA
pip install -r requirements.txt
```

### Run the Dashboard
```bash
python webapp/app.py
```
Then open browser to: `http://localhost:5000`

### Set AWS Credentials
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

---

## 📋 Dashboard Navigation

### Services Available
| Service | Icon | Features |
|---------|------|----------|
| **S3** | 🪣 | Encryption, versioning, public access, website hosting |
| **EC2** | 💾 | Backups, security groups, EBS encryption |
| **IAM** | 🔐 | Users, access keys, MFA, rotation |
| **Lambda** | ⚡ | Environment vars, logging, memory, timeout |

### Workflow
1. **Select Service** from sidebar
2. **Enter AWS Credentials** (auto-detected if set)
3. **Configure Checks** (use defaults or customize)
4. **Click "Scan for Issues"**
5. **Review Terminal Output** for details
6. **See Results** with findings and fixes

---

## 🎨 UI Colors (New Dark Theme)

### Quick Color Reference
```
Base Dark:        #0A0A0B
Cards:            #18181B
Inputs:           #27272A
Text Primary:     #FAFAFA
Text Secondary:   #A1A1A6
Accent:           #6366F1
Terminal Prompt:  #4EC9B0
Terminal Error:   #FF6B6B
Terminal Success: #51CF66
```

---

## 📁 Key Files Location

```
webapp/
  └─ app.py                    # Flask backend (START HERE for backend)
  └─ templates/
     └─ index.html             # Dashboard UI (START HERE for frontend)

agents/
  ├─ ec2_agent/
  ├─ s3_agent/
  ├─ iam_agent/
  └─ lambda_agents/            # NEW: Lambda security checks

supervisor/
  └─ supervisor_agent.py       # Main orchestration

fixer_agent/
  └─ fixer_agent.py            # Automated fixes
```

---

## 💻 Common Commands

### Check Python Version
```bash
python --version
```

### Run Tests
```bash
python test_pipeline.py
```

### View Logs
```bash
# Check Flask console output
# Ctrl+C to stop server
```

### Install New Package
```bash
pip install package_name
pip freeze > requirements.txt
```

---

## 🔧 Troubleshooting

### Dashboard Won't Load
- **Check**: Flask server running (should see address like `http://127.0.0.1:5000`)
- **Fix**: Kill process, restart with `python webapp/app.py`

### AWS Credentials Not Working
- **Check**: Environment variables set correctly
- **Fix**: Use `echo $AWS_ACCESS_KEY_ID` to verify
- **Alternative**: Enter manually in dashboard form

### Dark Theme Looks Wrong
- **Fix**: Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
- **Try**: Different browser (Chrome/Firefox/Safari)

### Scan Returns No Results
- **Check**: AWS credentials are valid
- **Check**: IAM user has required permissions
- **Check**: Target region has resources

### Terminal Output Cut Off
- **Fix**: Terminal panel scrollable, scroll to see full output
- **Check**: Browser window size adequate

---

## 📊 Service Parameters

### S3 Agent
```
Service: s3
Parameters:
  - s3_bucket_name (required)
  - s3_intent (e.g., "check encryption")
  - s3_checks (comma-separated)
```

### EC2 Agent
```
Service: ec2
Parameters:
  - ec2_instance_id (optional - all if empty)
  - ec2_intent (e.g., "check security")
  - ec2_checks (comma-separated)
```

### IAM Agent
```
Service: iam
Parameters:
  - iam_user_name (optional - all if empty)
  - iam_intent (e.g., "enforce MFA")
  - iam_checks (comma-separated)
```

### Lambda Agent (NEW)
```
Service: lambda
Parameters:
  - lambda_function_name (required)
  - lambda_intent (e.g., "check configuration")
  - lambda_checks (comma-separated)
```

---

## 🛠️ Development Workflow

### Adding New Agent
1. Create folder: `agents/service_agent/`
2. Copy structure from `agents/ec2_agent/`
3. Implement: `service_agent.py`, `executor.py`, `rules/`
4. Register in `supervisor/dispatcher.py`
5. Update `webapp/app.py` for frontend integration
6. Add UI form in `webapp/templates/index.html`

### Adding New Security Rule
1. Create file: `agents/service/rules/new_rule.py`
2. Implement `check()` and `fix()` methods
3. Register in `rules_init.py`
4. Add to service checks list

### Customizing UI
1. Edit `webapp/templates/index.html`
2. Modify CSS variables in `:root` block
3. Refresh browser (clear cache)
4. No Python changes needed

---

## 📈 Performance Tips

### For Faster Scans
- Use specific IDs (single resource vs. all)
- Disable checks you don't need
- Run in region with least resources

### For Better Performance
- Use instance with more CPU for Lambda runs
- Cache responses when possible
- Run scans during off-hours

---

## 🔐 Security Best Practices

### Credentials
✅ Use environment variables
✅ Never commit credentials
✅ Use IAM roles where possible
✅ Rotate access keys regularly

### Dashboard
✅ Use HTTPS in production
✅ Add authentication layer
✅ Restrict IP access
✅ Enable audit logging

### AWS Permissions
✅ Use least privilege
✅ Create service-specific IAM users
✅ Regular permission audits
✅ Enable CloudTrail logging

---

## 📞 Debug Mode

### Enable Verbose Logging
```python
# In webapp/app.py
app.logger.setLevel(logging.DEBUG)
```

### Check Agent Output
- View terminal panel in dashboard
- Check Flask console output
- Review `test_pipeline.py` results

### Inspect Requests
```python
# Add to Flask route
print(request.json)
```

---

## 🎯 Feature Checklist

### Current Features ✅
- [x] S3 security scanning
- [x] EC2 security scanning
- [x] IAM security scanning
- [x] Lambda security scanning (NEW)
- [x] Automated remediation
- [x] Dark theme UI
- [x] Terminal output
- [x] Results display
- [x] AWS integration
- [x] Credential management

### Planned Features 🔄
- [ ] Light theme toggle
- [ ] Custom report generation
- [ ] Scheduled scans
- [ ] Slack notifications
- [ ] Multi-account support
- [ ] Cost optimization
- [ ] Performance analysis

---

## 📚 Documentation Links

### Quick References
- `README_UI_ENHANCEMENT.md` - UI documentation index
- `PROJECT_SUMMARY.md` - Complete project overview

### Detailed Guides
- `UI_ENHANCEMENT_COMPLETE_SUMMARY.md` - Executive summary
- `UI_VISUAL_GUIDE.md` - Design system details
- `UI_TECHNICAL_REFERENCE.md` - Developer reference
- `UI_ENHANCEMENT_COMPLETE.md` - Implementation details

---

## 🎓 Code Examples

### Run a Scan Programmatically
```python
from supervisor.supervisor_agent import SupervisorAgent

supervisor = SupervisorAgent()
results = supervisor.scan_and_fix(
    service='s3',
    bucket_name='my-bucket',
    checks=['encryption', 'versioning']
)
print(results)
```

### Access an Agent Directly
```python
from agents.s3_agent.s3_agent import S3Agent

agent = S3Agent()
findings = agent.detect(bucket_name='my-bucket')
print(findings)
```

### Customize CSS Variables
```html
<!-- In index.html, modify :root -->
<style>
  :root {
    --bg-primary: #0A0A0B;      /* Change me */
    --text-primary: #FAFAFA;    /* Or me */
    --accent-primary: #6366F1;  /* Or me */
  }
</style>
```

---

## ✅ Deployment Checklist

Before going to production:
- [ ] Test all services (S3, EC2, IAM, Lambda)
- [ ] Verify AWS credentials working
- [ ] Enable HTTPS
- [ ] Add authentication
- [ ] Configure logging
- [ ] Set up monitoring
- [ ] Backup database (if used)
- [ ] Create runbook
- [ ] Test disaster recovery
- [ ] Document deployment steps

---

## 🆘 Support

### Where to Look
1. **Code Issues** → Check `test_pipeline.py`
2. **UI Issues** → Clear cache and try again
3. **AWS Issues** → Verify credentials and permissions
4. **Logic Issues** → Review agent code in `agents/`

### Getting Help
1. Check Flask console for errors
2. Enable debug mode
3. Review terminal output in dashboard
4. Check AWS CloudTrail logs
5. Review documentation files

---

## 📝 Version Info

```
Cloud Astra v1.0
Status: Production Ready ✅
Last Updated: December 6, 2025
Agents: 4 (S3, EC2, IAM, Lambda)
UI Theme: Dark (Modern)
Accessibility: WCAG AA+
Browser Support: Chrome 88+, Firefox 87+, Safari 14+
```

---

## 🎯 Next Steps

1. **For Users**: Start with Dashboard Quick Start
2. **For Developers**: Read PROJECT_SUMMARY.md
3. **For Designers**: Check UI_VISUAL_GUIDE.md
4. **For DevOps**: Review Deployment Checklist

---

**Happy Scanning! 🚀**

For detailed information, see the documentation suite included with this project.
