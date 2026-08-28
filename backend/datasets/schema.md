# Unified Dataset Index Schema

Each line in the index file is a JSON object with the following fields:

- `dataset`: `h36m` | `kinetics700` | `soccernet`
- `split`: `train` | `val` | `test` | `unknown`
- `clip_id`: string (stable id)
- `video_path`: string (absolute or repo-relative path)
- `label`: string (action/event label)
- `start_ms`: integer (optional, for event/action segments)
- `end_ms`: integer (optional, for event/action segments)
- `fps`: number (optional)
- `extra`: object (free-form metadata)

This index is used for training and evaluation across datasets.
