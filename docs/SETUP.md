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
| Android Studio | تشغيل التطبيق على أندرويد | `winget install --id google.androidstudio` (من غير `-e`: مع `-e` لازم الحروف الكبيرة والصغيرة تبقى مظبوطة) |
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

> في `backend/.env` كمان `PAYMENT_GATEWAY=fake` (شركة دفع تجريبية من غير فلوس حقيقية، من المرحلة 3). ده مش سر. لما حساب Paymob يجهز هنزود مفاتيحه هنا، ودي هتبقى أسرار.

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

**أول مرة بس على الجهاز** (اتجربت على لاب توب الشغل 17 نوفمبر 2026 ونجحت):

اللصقة دي بتجيب المشروع، وبتعمل **باسوردات جديدة للجهاز ده** وتكتبها في `backend/.env` من غير ما تظهر، وبتعمل قاعدة `bareeq` لوحدها، وتسطب المكتبات، وتجهز الجداول، وتضيف الفنيين التجريبيين، وتشغّل الاختبارات. هتسألك مرة واحدة على باسورد `postgres` (اللي اتعمل وقت تسطيب PostgreSQL). كلها حروف صغيرة عن قصد (شوف الملحوظة تحت).

PowerShell على جهازك (PS C:\):

```powershell
cd d:\bareeq; git pull
cd d:\bareeq\backend
if (test-path .env) { "env file already exists - send this to claude" } else {
  $p = -join ((97..122) | get-random -count 24 | % {[char]$_})
  $k = -join ((97..122) | get-random -count 50 | % {[char]$_})
  (get-content .env.example) -replace '^(django_secret_key=)$', ('${1}'+$k) -replace '^(db_password=)$', ('${1}'+$p) | set-content .env
  & "c:\program files\postgresql\16\bin\psql.exe" --username=postgres -c "create role bareeq login password '$p' createdb;" -c "create database bareeq owner bareeq encoding 'utf8';"
  py -3.12 -m venv .venv
  .\.venv\scripts\pip install -r requirements.txt
  .\.venv\scripts\python manage.py migrate
  .\.venv\scripts\python manage.py seed_demo_technicians
  .\.venv\scripts\python manage.py test --noinput
}
```

في الآخر لازم يظهر `Ran 280 tests` (أو أكتر) وتحته `OK`. بعدها افتح `notepad d:\bareeq\backend\.env` وانسخ محتواه في Bitwarden باسم `bareeq - <اسم الجهاز> backend .env` (مثلاً `bareeq - laptop backend .env`). كل جهاز ليه باسوردات قاعدة بيانات خاصة بيه.

> **ملحوظة مهمة (لاب توب الشغل):** وقت اللصق في PowerShell **الحروف الكبيرة بتختفي** (مثلاً `Get-PSDrive` بتوصل `et-rive`). عشان كده الأوامر هنا بحروف صغيرة، وPowerShell بيفهمها عادي. لو أمر فيه حروف كبيرة فشل بشكل غريب، اكتبه بحروف صغيرة.

> **صفحة الإدارة `/admin/`** (احتياطي لينا بس): لو احتجتها، `.\.venv\scripts\python manage.py createsuperuser` واحفظ الباسورد في Bitwarden باسم `bareeq - local admin`.

**حساب مدير للتطبيق** (بيدخل بالموبايل والكود، مش بباسورد):

```powershell
.\.venv\scripts\python manage.py create_manager --phone 01xxxxxxxxx --name "الاسم"
```

**كود الدخول وقت التجربة:** لسه مفيش شركة رسايل، فالكود مش بيتبعت SMS. بيظهر في شباك السيرفر في سطر شكله كده: `OTP for +2010XXXXXXXX: 123456`. ولو «وضع تجربة» شغال في جدول الإعدادات (وهو شغال دلوقتي)، الكود بيظهر كمان على شاشة الدخول نفسها.

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


### تشغيل التطبيق على موبايل أندرويد حقيقي (على اللاب توب)

**أول مرة بس:**
1. سطّب Android Studio (فوق في جدول البرامج). **التسطيب لوحده مش كفاية**: لازم تفتحه عشان ينزّل أدوات أندرويد (Android SDK)، حوالي 1 لـ 2 جيجا:
   - لو ظهر **Setup Wizard**: Next ← **Custom** ← في **Android SDK Location** اكتب `D:\Android\Sdk` ← Next ← Accept لكل الشروط ← Finish، واستنى التنزيل.
   - لو فتح على **Welcome**: More Actions ← **SDK Manager** ← **Android SDK Location** = `D:\Android\Sdk`، ومن تبويب **SDK Tools** علّم على **Android SDK Command-line Tools** ← OK.
   - بعدها: `flutter doctor --android-licenses` (اكتب `y` في كل سؤال)، وبعدين `flutter doctor` لازم سطر **Android toolchain** يبقى عليه ✓.
   - للتأكد إن الأدوات موجودة: `test-path d:\android\sdk` لازم يطلع `True`.
2. على الموبايل: الإعدادات ← عن الهاتف ← دوس على «رقم الإصدار» 7 مرات، وبعدين من «خيارات المطور» شغّل «تصحيح أخطاء USB». وصّل الموبايل باللاب توب بالكابل ووافق على الرسالة اللي هتظهر على الموبايل.
3. اعرف عنوان اللاب توب على الشبكة: في PowerShell اكتب `ipconfig` وخد الرقم اللي جنب «IPv4 Address» (شكله زي 192.168.1.10). الموبايل واللاب توب لازم يكونوا على نفس الواي فاي.
4. في `backend/.env` زوّد الرقم ده في `DJANGO_ALLOWED_HOSTS`، مثلاً: `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.10`

**كل مرة:**

PowerShell على جهازك (PS C:\) — شباك السيرفر:

```powershell
cd D:\bareeq\backend
.\.venv\Scripts\python manage.py runserver 0.0.0.0:8000
```

(لو Windows سألك عن الـ Firewall، وافق على «Private networks».)

PowerShell على جهازك (PS C:\) — شباك تاني للتطبيق (حط رقم اللاب توب مكان 192.168.1.10):

```powershell
cd D:\bareeq\mobile
flutter run --dart-define=API_BASE=http://192.168.1.10:8000/api
```

قايمة الحاجات اللي لازم تتجرب على الموبايل: `docs/PHONE-TEST-ar.md`.


### لينك تجربة للعميل (من الموبايل، أندرويد أو آيفون، من غير تسطيب)

السيرفر والتطبيق بيشتغلوا على اللاب توب، وبرنامج مجاني (Cloudflare Tunnel، من غير حساب) بيدّيهم لينك مؤقت على الإنترنت. العميل يفتح اللينك من متصفح موبايله ويجرب كل حاجة. وضع التجربة لازم يكون شغال، عشان كود الدخول يظهر على الشاشة.

- **اللينك شغال بس واللاب توب مفتوح والشباك شغال.** وبيتغير كل مرة تشغله، فلازم تبعت للعميل اللينك الجديد.
- البيانات اللي العميل بيعملها بتتحفظ في قاعدة `bareeq` على اللاب توب.
- ⚠️ طول ما وضع التجربة شغال، أي حد معاه اللينك ويعرف رقم حساب يقدر يدخل بيه. فمتنشرش اللينك، وابعته للعميل بس.

**أول مرة بس:** سطّب البرنامج، وبعدين اقفل PowerShell وافتحه تاني.

PowerShell على جهازك (PS C:\):

```powershell
winget install --id cloudflare.cloudflared --accept-package-agreements --accept-source-agreements
```

**كل مرة عايز تدّي العميل لينك:**

PowerShell على جهازك (PS C:\):

```powershell
cd d:\bareeq; git pull; powershell -executionpolicy bypass -file d:\bareeq\scripts\demo-link.ps1 -rebuild
```

(`-rebuild` بيعيد تجهيز التطبيق، وده بياخد كام دقيقة. لو مسحبتش حاجة جديدة من GitHub شيله.)

في الآخر هيظهر سطر أصفر فيه اللينك (شكله `https://....trycloudflare.com`)، وبيتنسخ لوحده، فتقدر تلصقه للعميل على واتساب. وهيفتح شباك تاني للسيرفر، وأكواد الدخول بتظهر فيه كمان. سيب الشباكين مفتوحين، ولما تخلص دوس Enter في الشباك الأولاني.
