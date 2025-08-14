# indralib (Common Lisp)

Initial Common Lisp port scaffolding for IndraLib.

- System: `indralib` (ASDF)
- Features: `indra-event` port, JSON encode/decode, MQTT-style wildcard compare, `indra-time` utilities
- Dependencies: [`yason`](https://github.com/phmarek/yason), [`uuid`](https://github.com/dardoria/cl-uuid) (ASDF names `yason` and `uuid`)

## Load

In a Lisp REPL with Quicklisp:

```
(ql:quickload :indralib)
```

Or with ASDF (ensure the project directory is in `asdf:*central-registry*` or source registry):

```
(asdf:load-system :indralib)
```

## Usage

```
(defparameter *e* (indra:make-indra-event
                   :domain "a/b/c"
                   :from-id "client/xyz"
                   :data-type "text/plain"
                   :data "hello"))

(format t "~a~%" (indra:event-to-json *e*))

(indra:mqcmp "a/b/c" "a/+/#") ; => T

;; Time API
(indra:julian-to-iso (indra:discrete-time-to-julian 2020 1 1 0 0 0 0))
```

## Notes

- `now-julian-date` is a small helper in lieu of a full `indra_time` port.
- JSON keys follow the Python field names (e.g., `from_id`, `parent_uuid4`, etc.).
