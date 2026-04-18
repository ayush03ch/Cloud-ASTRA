# CloudASTRA

CloudASTRA is a multi-agent AWS security scanner with guided remediation.

It scans AWS services for common misconfigurations, explains findings by severity, and supports targeted fixes (including auto-fix for selected checks).

## Features

- Multi-service scanning through one dashboard.
- Rule-based findings with optional LLM fallback.
- Tiered output (critical, medium, low) for faster triage.
- Manual fix workflows with service-specific actions.
- Auto-fix support for selected issues (for example in CloudFront and Route53 flows).

## Supported Services

- S3
- EC2
- IAM
- Lambda
- Route53
- API Gateway
- CloudFront
- VPC

## Project Structure

```text
CloudASTRA-II/
|- agents/                # Service-specific analyzers and rules
|- fixer_agent/           # Remediation executor and fix orchestration
|- supervisor/            # Dispatching and orchestration layer
|- webapp/                # Flask app + templates + static assets
|- knowledge_base/        # Service docs and guidance notes
|- test_pipeline.py
|- test_query_logging_rule.py
|- test_route53_agent.py
`- startup.sh
```

## Architecture

1. Dashboard sends scan request to `/api/scan`.
2. Supervisor assumes role and routes by service.
3. Service agent runs rules and returns findings.
4. Fixer agent applies requested fixes (auto or manual).
5. Dashboard renders summary, findings, and fix status.

## Prerequisites

- Python 3.10+
- AWS account access with an assumable IAM role
- External ID configured in trust policy

## Local Setup

### 1) Clone and create virtual environment

```bash
git clone <your-repo-url>
cd CloudASTRA-II
python -m venv .venv
```

### 2) Activate environment

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Configure environment

Create a `.env` file at repo root if needed by your setup. Typical values include LLM keys and app configs

### 5) Run the app

From repo root:

```bash
python webapp/app.py
```

Open `http://localhost:5000`.

## Running Tests

Run available tests directly:

```bash
python test_pipeline.py
python test_query_logging_rule.py
python test_route53_agent.py
```

## AWS Role Requirements

At minimum, the assumed role needs:

- Read/list permissions for scanned services.
- Update permissions for fixes you plan to apply.
- Extra permissions for provisioning side effects (example: CloudFront logging fix may need S3 bucket create/configure permissions).

If a fix fails with `AccessDenied`, verify IAM policy scope before retrying.

## API Endpoints

- `GET /` - Landing page
- `GET /dashboard` - Main scanner UI
- `POST /api/scan` - Run scan and optional auto-fix
- `POST /api/apply-manual-fix` - Apply targeted fix

## Deployment

The repo includes `startup.sh` for App Service style startup (venv setup, dependency install, Gunicorn launch).

## Contributing

1. Create a feature branch.
2. Keep changes scoped and service-specific where possible.
3. Add or update tests for behavior changes.
4. Open a PR with:
   - What changed
   - Why it changed
   - How you validated it

## Troubleshooting

- Role assumption fails: validate trust relationship and external ID.
- Empty findings unexpectedly: confirm selected service and scan scope.
- Auto-fix disabled: ensure finding metadata marks it auto-fixable and backend route passes required fields.
- LLM enrichment missing: check your environment key configuration.

## License

Add your project license here (for example, MIT).