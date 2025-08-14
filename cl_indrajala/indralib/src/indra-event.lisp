;;;; indra-event.lisp — Common Lisp port of Python indra_event.py (subset)

(in-package #:indralib)

;; Simple UUID v4 generator (random-based). Not cryptographically strong.
(defun uuid-v4-string ()
  (labels ((rand-byte () (random 256))
           (hex2 (b)
             (format nil "~2,'0x" b)))
    (let* ((bytes (make-array 16 :element-type '(unsigned-byte 8)))
           (i 0))
      (loop for i from 0 below 16 do (setf (aref bytes i) (rand-byte)))
      ;; Set version (4) and variant (10xx)
      (setf (aref bytes 6) (logior #x40 (logand (aref bytes 6) #x0F)))
      (setf (aref bytes 8) (logior #x80 (logand (aref bytes 8) #x3F)))
      (format nil "~a~a~a~a-~a~a-~a~a-~a~a-~a~a~a~a~a~a"
              (hex2 (aref bytes 0)) (hex2 (aref bytes 1)) (hex2 (aref bytes 2)) (hex2 (aref bytes 3))
              (hex2 (aref bytes 4)) (hex2 (aref bytes 5))
              (hex2 (aref bytes 6)) (hex2 (aref bytes 7))
              (hex2 (aref bytes 8)) (hex2 (aref bytes 9))
              (hex2 (aref bytes 10)) (hex2 (aref bytes 11)) (hex2 (aref bytes 12)) (hex2 (aref bytes 13)) (hex2 (aref bytes 14)) (hex2 (aref bytes 15))))))

;; A minimal replacement for IndraTime.datetime_to_julian(now_utc)
;; We don't yet port full indra_time; use current UTC time converted to JD.
(defun now-julian-date ()
  "Return current UTC time as a Julian Date (double-float)."
  (let* ((unix-epoch-to-jd 2440587.5d0)
         (now-sec (get-universal-time))
         ;; CL universal time is seconds since 1900-01-01; Unix epoch = 1970-01-01.
         ;; Difference between CLUT and Unix epoch in seconds:
         (clut-unix-delta (* 2208988800 1))
         (unix-seconds (- now-sec clut-unix-delta))
         (jd (+ unix-epoch-to-jd (/ (coerce unix-seconds 'double-float)
                                     86400.0d0))))
    jd))

(defclass indra-event ()
  ((domain :initarg :domain :initform "" :accessor event-domain)
   (from-id :initarg :from-id :initform "" :accessor event-from-id)
  (uuid4 :initarg :uuid4 :initform (uuid-v4-string) :accessor event-uuid4)
   (parent-uuid4 :initarg :parent-uuid4 :initform "" :accessor event-parent-uuid4)
   (seq-no :initarg :seq-no :initform 0 :accessor event-seq-no)
   (to-scope :initarg :to-scope :initform "" :accessor event-to-scope)
   (time-jd-start :initarg :time-jd-start :initform (now-julian-date) :accessor event-time-jd-start)
   (data-type :initarg :data-type :initform "" :accessor event-data-type)
   (data :initarg :data :initform "" :accessor event-data)
   (auth-hash :initarg :auth-hash :initform "" :accessor event-auth-hash)
   (time-jd-end :initarg :time-jd-end :initform nil :accessor event-time-jd-end)))

(defun make-indra-event (&key domain from-id uuid4 parent-uuid4 seq-no to-scope
                           time-jd-start data-type data auth-hash time-jd-end)
  (make-instance 'indra-event
                 :domain domain
                 :from-id from-id
                 :uuid4 (or uuid4 (uuid-v4-string))
                 :parent-uuid4 parent-uuid4
                 :seq-no (or seq-no 0)
                 :to-scope to-scope
                 :time-jd-start (or time-jd-start (now-julian-date))
                 :data-type data-type
                 :data data
                 :auth-hash auth-hash
                 :time-jd-end time-jd-end))

(defun event-version (_event)
  "Return version string."
  "02")

(defun event-old-versions (_event)
  '("" "01"))

(defun event-to-plist (event)
  "Return a property list representation similar to Python fields (for introspection)."
  (list :domain (event-domain event)
        :from_id (event-from-id event)
        :uuid4 (event-uuid4 event)
        :parent_uuid4 (event-parent-uuid4 event)
        :seq_no (event-seq-no event)
        :to_scope (event-to-scope event)
        :time_jd_start (event-time-jd-start event)
        :data_type (event-data-type event)
        :data (event-data event)
        :auth_hash (event-auth-hash event)
        :time_jd_end (event-time-jd-end event)))

(defun event-to-hash (event)
  "Return a hash-table mapping JSON string keys to values for stable YASON encoding."
  (let ((ht (make-hash-table :test 'equal)))
    (setf (gethash "domain" ht) (event-domain event)
          (gethash "from_id" ht) (event-from-id event)
          (gethash "uuid4" ht) (event-uuid4 event)
          (gethash "parent_uuid4" ht) (event-parent-uuid4 event)
          (gethash "seq_no" ht) (event-seq-no event)
          (gethash "to_scope" ht) (event-to-scope event)
          (gethash "time_jd_start" ht) (event-time-jd-start event)
          (gethash "data_type" ht) (event-data-type event)
          (gethash "data" ht) (event-data event)
          (gethash "auth_hash" ht) (event-auth-hash event)
          (gethash "time_jd_end" ht) (event-time-jd-end event))
    ht))

(defun event-to-json (event)
  "Encode event to a JSON string."
  (with-output-to-string (s)
    (yason:encode (event-to-hash event) s)))

(defun event-from-json (json-string)
  "Decode JSON and construct an indra-event. Accepts keys with Python-style names."
  (let* ((obj (yason:parse json-string :object-as :hash-table))
    (get (lambda (k)
      (or (gethash k obj)
          (gethash (string-downcase (string k)) obj)))))
    (make-indra-event
     :domain (funcall get "domain")
     :from-id (funcall get "from_id")
     :uuid4 (funcall get "uuid4")
     :parent-uuid4 (funcall get "parent_uuid4")
     :seq-no (or (funcall get "seq_no") 0)
     :to-scope (funcall get "to_scope")
     :time-jd-start (funcall get "time_jd_start")
     :data-type (funcall get "data_type")
     :data (funcall get "data")
     :auth-hash (funcall get "auth_hash")
     :time-jd-end (funcall get "time_jd_end"))))

(defun mqcmp (pub sub)
  "MQTT-style wildcard compare. PUB must not contain '+' or '#'. SUB may use them."
  (labels ((illegal-p (s)
             (or (position #\+ s) (position #\# s)))
           (char-at (s i)
             (and (<= 0 i) (< i (length s)) (char s i))))
    (when (illegal-p pub)
      (format *error-output* "Illegal char '+' or '#' in pub in mqcmp!~%")
      (return-from mqcmp nil))
    (let ((inds 0)
          (wcs nil)
          (lenp (length pub))
          (lens (length sub)))
      (loop for indp from 0 below lenp do
           (cond
             (wcs
              (when (char= (char-at pub indp) #\/)
                (incf inds)
                (setf wcs nil)))
             (t
              (when (>= inds lens) (return-from mqcmp nil))
              (let ((cp (char-at pub indp))
                    (cs (char-at sub inds)))
                (cond
                  ((and cp cs (char= cp cs))
                   (incf inds))
                  ((and cs (char= cs #\#)) (return-from mqcmp t))
                  ((and cs (char= cs #\+))
                   (setf wcs t)
                   (incf inds))
                  (t (return-from mqcmp nil)))))))
      (let* ((rest (- lens inds)))
        (cond
          ((= rest 0) t)
          ((= rest 1)
           (let ((cs (char-at sub inds)))
             (or (char= cs #\+) (char= cs #\#))))
          (t nil))))))
