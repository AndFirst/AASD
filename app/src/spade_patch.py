"""
Eliminuje błąd
Exception in the event loop: ClientXMPP.connect() got an unexpected keyword argument 'address'
Wystarczy zaimportować raz w main.py i powinno działać dla całego programu.
"""

import slixmpp

# --- Patch SPADE / slixmpp ---
_old_connect = slixmpp.ClientXMPP.connect


def patched_connect(self, *args, **kwargs):
    if "address" in kwargs:
        host, port = kwargs.pop("address")
        return _old_connect(self, host=host, port=port)
    return _old_connect(self, *args, **kwargs)


slixmpp.ClientXMPP.connect = patched_connect
# ------------------------------

print("[PATCH] slixmpp.ClientXMPP.connect patched for SPADE compatibility.")
