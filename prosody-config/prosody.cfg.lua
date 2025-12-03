pidfile = "/var/run/prosody/prosody.pid"

admins = { }

modules_enabled = {
    "roster"; 
    "saslauth";
    "tls";
    "dialback";
    "disco";
    "posix";
    "register";
}

modules_disabled = {
}

allow_registration = true

c2s_require_encryption = false
s2s_require_encryption = false

authentication = "internal_plain"

log = {
    info = "/var/log/prosody/prosody.log";
    error = "/var/log/prosody/prosody.err";
}

VirtualHost "localhost"
