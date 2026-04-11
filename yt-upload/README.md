# Upload Tool (アップツール)

Automated upload system with agent-based workflow and human verification.

## Components
- `agents/`: PowerShell/Python agents for searching, checking, and uploading
  - `searcher.py`: Find content ready for upload
  - `checker.py`: Verify all required assets are present
  - `automation/`: PDF-to-video pipeline (main.py, local_run.py, colab_runner.py)
  - `upload_meeting.py`: OAuth YouTube upload script
  - `upload_meeting_gcloud.py`: Google Cloud ADC YouTube upload script
- `workflows/`: Defined upload workflows
  - `config/`: Content pool, frame specs (15s format)
- `human-review/`: Interface for final human verification

## Workflow
1. Agents search for completed content
2. System checks completion status
3. Automated upload process (OAuth or gcloud ADC)
4. Final human verification before publishing
