   #!/bin/bash
   # start.sh
   gunicorn app:app --bind 0.0.0.0:$PORT