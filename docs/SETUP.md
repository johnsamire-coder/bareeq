# بريق — تجهيز لاب توب جديد من الصفر

الملف ده بيتحدث مع كل خطوة. لو نقلت على جهاز جديد، امشي عليه بالترتيب.
كل الأوامر هنا بتتكتب في **PowerShell على جهازك (PS C:\)**.

## 1. البرامج الأساسية

| البرنامج | لازمته | أمر التسطيب |
|---|---|---|
| Git | حفظ الشغل ورفعه على GitHub | `winget install --id Git.Git -e` |

> باقي البرامج (Python و PostgreSQL و Node و Flutter) هتتضاف هنا بالنسخ المضبوطة بعد الخطوة 1.

بعد التسطيب اقفل PowerShell وافتحه تاني.

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
| (لسه مفيش) | | |

## 4. Claude Code

```powershell
irm https://claude.ai/install.ps1 | iex
cd D:\bareeq
claude
```

أول ما يفتح قوله: «اقرا docs/PROGRESS.md وكمل من مكان ما وقفنا».

## 5. تشغيل أجزاء البرنامج

> بيتضاف هنا بعد كل خطوة (السيرفر بعد الخطوة 2، والتطبيق بعد الخطوة 11، ولوحة المدير بعد الخطوة 13).
