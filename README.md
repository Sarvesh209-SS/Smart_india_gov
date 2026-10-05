# SMART INDIA GOV (foundation)
Independent assistance platform, not an official Government of India site.

## Setup
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    py -3 -m pip install -r requirements.txt
    Copy-Item .env.example .env # fill in secrets
    mysql -u root -p -e "CREATE DATABASE smart_india_gov CHARACTER SET utf8mb4; CREATE USER 'sig_user'@'localhost' IDENTIFIED BY '...'; GRANT ALL ON smart_india_gov.* TO 'sig_user'@'localhost';"
    redis-server &
    py -3 manage.py migrate
    py -3 manage.py createsuperuser
    py -3 manage.py runserver 127.0.0.1:8000

## Account Security
Registration and login use Django email/password authentication. An Indian mobile number is optional contact information only; the site does not send SMS or require OTP. Password validation, secure password hashing, session expiry, and logout-all-devices session invalidation remain enabled.

Create the first administrator with `py -3 manage.py createsuperuser`. Existing superusers are migrated to the `SUPER_ADMIN` role. Reviewer queue access also requires both staff status and a reviewer/admin role.

## Language Support
The interface uses Django gettext keys with English, Tamil (`ta`), and Hindi (`hi`) catalogs under `locale/`. Compiled `.mo` catalogs are included. To rebuild after editing `.po` files, install GNU gettext and run `py -3 manage.py compilemessages`. The selected language is saved to the signed-in user's profile.

## Private Document Locker and Portfolio
Sign in and open `/documents/upload/` to upload PDF, DOC, DOCX, TXT, JPG, JPEG, or PNG files (maximum 5 MB). The locker includes Aadhaar, community, income, nativity, birth, PAN, bank passbook, 10th, 12th, and graduation certificate categories. Upload progress is shown in the browser. Files are private; users can view, download, and delete only their own documents. Rejected documents keep their reason and history when a student uploads a replacement. Portfolio completion counts verified documents among the ten standard certificate categories.

Open `/documents/portfolio/` for the generated private portfolio. It groups saved documents under certificate headings and includes the account's profile details. Uploaded file metadata is saved in Django's database.

Local development uses the existing private filesystem backend (`private_media/`) and requires no Firebase configuration. To use Firebase Storage instead, add both values below to `.env`:

```dotenv
FIREBASE_STORAGE_BUCKET=your-project-id.firebasestorage.app
FIREBASE_SERVICE_ACCOUNT_KEY=C:\\secure\\path\\firebase-service-account.json
```

Use the exact bucket name shown in Firebase Console > Storage. Create a service-account JSON key in Firebase Console > Project settings > Service accounts; keep the key outside public/static folders and never commit it. Grant that service account object read, create, and delete permissions on the bucket. Deploy `firebase.storage.rules`; client SDK reads/writes are denied because document access is mediated by authenticated Django views and the Admin SDK.

Document verification in this application means review by an authorized staff member. No authorized DigiLocker API/OAuth integration is configured; the site does not claim official DigiLocker verification or ask for DigiLocker credentials. Uploaded documents are never treated as externally verified.

## Tests
Run `py -3 manage.py test` for the full account, document, review, and scholarship test suite.

## Production Deployment
Set `DJANGO_DEBUG=0`, a unique `DJANGO_SECRET_KEY`, production `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` (full HTTPS origins), MySQL credentials, and a reachable Redis `REDIS_URL`. Put Django behind an HTTPS reverse proxy; production settings redirect HTTP and enable secure session/CSRF cookies and HSTS. The proxy must strip and set `X-Forwarded-Proto` itself; do not expose the application server directly when trusting that header. Run `py -3 manage.py migrate` and `py -3 manage.py collectstatic`, then serve `config.asgi:application` with Daphne behind the proxy. Back up the SQL database and private file store and restrict service-account IAM to the storage bucket. For Firebase storage, set both Firebase variables and deploy `firebase.storage.rules`; this Django project does not use Firebase Authentication or Firestore.

## Test WebSocket notification
In browser console while logged in: `new WebSocket("ws://127.0.0.1:8000/ws/notifications/").onmessage=e=>console.log(e.data)`
Then in admin publish a Scholarship with a rule, and save your UserProfile: a notification arrives live.

## Not Yet Built
DRF APIs, Celery reminders, exams/rules/contacts apps, and animated logo.
