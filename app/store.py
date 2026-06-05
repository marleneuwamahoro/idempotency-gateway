

import threading

idempotency_store = {}


processing_events = {}

store_lock = threading.Lock()
