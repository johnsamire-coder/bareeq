# بريق — تجهيز لاب توب جديد من الصفر

الملف ده بيتحدث مع كل خطوة. لو نقلت على جهاز جديد، امشي عليه بالترتيب.
كل الأوامر هنا بتتكتب في **PowerShell على جهازك (PS C:\)**.

## 1. البرامج الأساسية

| البرنامج | لازمته | أمر التسطيب |
|---|---|---|
| Git | حفظ الشغل ورفعه على GitHub | `winget install --id Git.Git -e` |
| Python 3.12 | السيرفر (Django) | `winget install --id Python.Python.3.12 -e` |
| PostgreSQL 16 | قاعدة البيانات | `winget install --id PostgreSQL.PostgreSQL.16 -e` |
| Node.js (النسخة LTS، 24) | مش محتاجينه دلوقتي (كان للوحة الويب اللي اتشالت). سيبه لو متسطب | `winget install --id OpenJS.NodeJS.LTS -e` |
| Java 17 | مطلوب لتطبيق أندرويد | `winget install --id Microsoft.OpenJDK.17 -e` |
| Android Studio | تشغيل التطبيق على أندرويد | `winget install --id Google.AndroidStudio -e` |
| Flutter 3.44 (stable) | تطبيق الموبايل | مش موجود في winget. نزّل الـ zip من docs.flutter.dev وفكه في `D:\src\flutter` وضيف `D:\src\flutter\bin` للـ Path |

ملاحظات:
- **PostgreSQL:** وقت التسطيب هيسألك على باسورد للمستخدم `postgres`. احفظه في Bitwarden فوراً باسم `PostgreSQL postgres (local)`.
- **Android Studio:** بعد ما يتسطب افتحه مرة، وخليه ينزّل الـ Android SDK في `D:\Android\Sdk` عشان الـ C: مساحته قليلة. بعدين نفّذ `flutter doctor --android-licenses` ووافق على كله.
- لو في أكتر من نسخة Python على الجهاز، استخدم دايماً `py -3.12`.
- التطبيق بيتعمل لأندرويد من الجهاز ده. نسخة الآيفون محتاجة جهاز ماك (هنتكلم فيها بعدين).

بعد التسطيب اقفل PowerShell وافتحه تاني، وبعدين اتأكد إن كله تمام بالأمر ده:

```powershell
git --version; py -3.12 --version; node --version; flutter doctor
```

## 2. هات المشروع من GitHub

```powershell
cd D:\
git clone https://github.com/johnsamire-coder/bareeq.git
cd D:\bareeq
git config user.name "johnsamire-coder"
git config user.email "jssolutions.eg@gmail.com"
```

أول مرة ترفع حاجة هيطلب منك تسجل دخول GitHub من المتصفح. وافق.

## 3. الأسرار (الباسوردات والمفاتيح)

الأسرار **مش موجودة على GitHub** خالص، وده مقصود. مكانها:

- **المكان الأساسي:** برنامج حفظ باسوردات. المقترح **Bitwarden** وهو مجاني (bitwarden.com)، تفتحه من الموبايل ومن أي جهاز. كل سر بيتحفظ فيه كـ "Secure Note" باسم واضح، مثلاً `bareeq - backend .env`.
- **على الجهاز:** في ملفات `.env` جوه المشروع. الملفات دي GitHub بيتجاهلها.

على الجهاز الجديد: لكل ملف في الجدول ده، اعمل نسخة من `.env.example` اللي جنبه باسم `.env`، وحط فيها القيم من Bitwarden.

| الملف | فيه إيه | اتعمل في |
|---|---|---|
| `backend/.env` | مفتاح Django السري (`DJANGO_SECRET_KEY`)، وباسورد قاعدة البيانات (`DB_PASSWORD`) | الخطوة 2 |

## 4. Claude Code

```powershell
irm https://claude.ai/install.ps1 | iex
cd D:\bareeq
claude
```

أول ما يفتح قوله: «اقرا docs/PROGRESS.md وكمل من مكان ما وقفنا».

## 5. تشغيل أجزاء البرنامج

> بيتضاف هنا بعد كل خطوة. (مفيش لوحة ويب: شاشات المدير جوه نفس التطبيق.)

### السيرفر (Django) — من الخطوة 2

**أول مرة بس على الجهاز:**

1) اعمل مستخدم وقاعدة بيانات `bareeq` (منفصلين تماماً عن أي حاجة تانية على الجهاز). الأمر ده هيسألك على باسورد `postgres`.
حط مكان `PASTE_DB_PASSWORD` الباسورد اللي في Bitwarden (`bareeq - backend .env`، السطر `DB_PASSWORD`).

PowerShell على جهازك (PS C:\):

```powershell
psql -U postgres -c "CREATE ROLE bareeq LOGIN PASSWORD 'PASTE_DB_PASSWORD' CREATEDB;" -c "CREATE DATABASE bareeq OWNER bareeq ENCODING 'UTF8';"
```

2) جهّز بيئة بايثون الخاصة بالمشروع، وملف الأسرار، وجداول قاعدة البيانات.

PowerShell على جهازك (PS C:\):

```powershell
cd D:\bareeq\backend
py -3.12 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
notepad .env
```

في Notepad حط قيم `DJANGO_SECRET_KEY` و `DB_PASSWORD` من Bitwarden واحفظ. وبعدين:

```powershell
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py createsuperuser
```

(الأمر الأخير بيعمل حساب دخول لصفحة الإدارة. هيسألك على رقم موبايل واسم وباسورد. احفظ الباسورد في Bitwarden باسم `bareeq - local admin`.)

> **ملحوظة:** لو كنت شغّلت `migrate` على جهازك قبل الخطوة 3، جدول المستخدمين اتغير. امسح قاعدة البيانات واعملها تاني (هي فاضية أصلاً):
> `psql -U postgres -c "DROP DATABASE bareeq;" -c "CREATE DATABASE bareeq OWNER bareeq ENCODING 'UTF8';"` وبعدين `migrate` تاني.

**حساب مدير للتطبيق** (بيدخل بالموبايل والكود، مش بباسورد):

```powershell
.\.venv\Scripts\python manage.py create_manager --phone 01XXXXXXXXX --name "الاسم"
```

**كود الدخول وقت التجربة:** لسه مفيش شركة رسايل، فالكود مش بيتبعت SMS. بيظهر في شباك السيرفر في سطر شكله كده: `OTP for +2010XXXXXXXX: 123456`.

**الصور:** صور قبل وبعد بتتحفظ في فولدر `backend/media/` (مش بيترفع على GitHub). لو نقلت الجهاز، الصور مش هتتنقل معاه. على السيرفر الحقيقي هنحطها في مكان آمن ونعمل لها نسخة احتياطية.

**فنيين تجريبيين (للتجربة بس، مش على السيرفر الحقيقي):**

```powershell
.\.venv\Scripts\python manage.py seed_demo_technicians
```

**الأوامر اللي بتشتغل لوحدها:** على السيرفر الحقيقي الأمر ده لازم يشتغل أوتوماتيك كل 5 دقايق. هو بيعمل كل اللي تحت (الحجز المؤقت، ورصيد المحفظة، وكل التذكيرات)، ومينفعش يبعت نفس التذكير مرتين: `python manage.py run_scheduled_jobs`

**الحجز المؤقت:** الحجز اللي العميل مدفعش فيه بيتساب لوحده بعد 10 دقايق. على السيرفر الحقيقي لازم الأمر ده يشتغل أوتوماتيك كل كام دقيقة (هنظبطه وقت الرفع على السيرفر): `python manage.py expire_holds`

**رصيد المحفظة اللي صلاحيته خلصت:** على السيرفر الحقيقي الأمر ده لازم يشتغل أوتوماتيك مرة كل يوم: `python manage.py expire_wallet_credits`

**الشروط:** التسجيل مقفول لحد ما تتنشر أول نسخة من الشروط. من صفحة الإدارة: «نسخ الشروط» ← «إضافة». كل تعديل بيتعمل كنسخة جديدة.

**كل مرة عايز تشغل السيرفر:**

```powershell
cd D:\bareeq\backend
.\.venv\Scripts\python manage.py runserver
```

افتح في المتصفح: `http://127.0.0.1:8000/api/health/` لازم يظهر `"status":"ok"`. وصفحة الإدارة: `http://127.0.0.1:8000/admin/`

**الاختبارات:**

```powershell
.\.venv\Scripts\python manage.py test
```


### تطبيق الموبايل (Flutter) — من الخطوة 11

**أول مرة بس:** في ملف `backend/.env` لازم يبقى فيه السطر ده (عشان المتصفح يقدر يكلم السيرفر):
`CORS_ALLOWED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080`

**تشغيل التطبيق على Chrome** (السيرفر لازم يكون شغال في شباك تاني).

PowerShell على جهازك (PS C:\):

```powershell
cd D:\bareeq\mobile
flutter pub get
flutter run -d chrome --web-port 8080
```

كود الدخول بيظهر في شباك السيرفر (زي ما اتشرح فوق).

**الاختبارات:**

```powershell
cd D:\bareeq\mobile
flutter test
```

> لو سحبت شغل جديد من GitHub فيه مكتبة جديدة، وظهر خطأ زي `MissingPluginException`: شغّل `flutter clean` وبعدين `flutter pub get` وجرب تاني.

> **الخريطة:** شاشة العنوان بتستخدم OpenStreetMap **مؤقتاً للتجربة بس**، ولازم تتبدل بخريطة جوجل قبل الإطلاق.
