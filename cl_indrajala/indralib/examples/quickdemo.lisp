;; quickdemo.lisp — small demo to try in a REPL

(ql:quickload :indralib)

(defparameter *e* (indra:make-indra-event
                   :domain "a/b/c"
                   :from-id "client/xyz"
                   :data-type "text/plain"
                   :data "hello"))

(format t "~a~%" (indra:event-to-json *e*))

(assert (eq t (indra:mqcmp "a/b/c" "a/+/#")))
