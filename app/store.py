# app/store.py
# ------------------------------------------------------------------
# This acts as our in-memory database.
# In a real production app, you would replace this with Redis or SQLite.
#
# Structure of idempotency_store:
# {
#   "some-unique-key": {
#       "status": "processing" | "done",
#       "request_body_hash": "abc123...",
#       "response_body": {...},
#       "response_status": 201,
#   }
# }
# ------------------------------------------------------------------

import threading

# Our in-memory store: a plain Python dictionary
idempotency_store = {}

# A dictionary of threading Events — used to handle race conditions.
# When Request A is processing, Request B will WAIT on this event
# until Request A is done.
processing_events = {}

# A lock ensures that only ONE thread at a time can check/modify
# the store. This prevents race conditions.
store_lock = threading.Lock()
