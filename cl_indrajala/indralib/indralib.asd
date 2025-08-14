;;;; indralib.asd — ASDF system definition for the Common Lisp port of IndraLib

(asdf:defsystem #:indralib
  :description "Common Lisp IndraLib core — initial port with IndraEvent"
  :author "Indrajala contributors"
  :license "MIT"
  :version "0.0.1"
  :depends-on (#:yason #:alexandria #:parse-number)
  :serial t
  :components
  ((:module "src"
    :serial t
    :components ((:file "packages")
                 (:file "indra-event")
                 (:file "indra-time")))))
