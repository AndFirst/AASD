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

allow_registration = true

c2s_require_encryption = true

authentication = "internal_hashed"

log = {
    info = "/var/log/prosody/prosody.log";
    error = "/var/log/prosody/prosody.err";
}

VirtualHost "localhost"
ssl = {
    key = "/var/lib/prosody/localhost.key";
    certificate = "/var/lib/prosody/localhost.crt";
}