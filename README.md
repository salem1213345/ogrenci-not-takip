<div dir="rtl">

# AkademiPusula — نظام متابعة درجات الطلاب (Öğrenci Not Takip Sistemi)

تطبيق سطح مكتب مكتوب بـ Python و Tkinter و SQLite، لا يحتاج إلى خادم قاعدة بيانات. يدير الطلاب
والمقررات والدرجات، ويحسب المعدل الموزون والتقدير الحرفي والمعدل التراكمي (GNO)، ويُصدر تقارير
PDF و CSV، ويحتوي على واجهتين: لوحة المعلّم وبوابة الطالب، مع نظام رسائل.

> النسخة التركية الكاملة من التوثيق موجودة في الملف [README.tr.md](README.tr.md).

## المتطلبات

| المتطلب | التفاصيل |
|---|---|
| نظام التشغيل | Windows 10 أو 11 |
| بايثون | **Python 3.11 أو أحدث** (تم الاختبار على Python 3.15.1). يجب أن يتضمن Tkinter، وهو مضمَّن افتراضيًا في مثبّت python.org |
| الإنترنت | مطلوب **مرة واحدة فقط** عند التشغيل الأول لتنزيل المكتبات من `requirements.txt` |
| المكتبات | `fpdf2==2.8.9`، `defusedxml==0.7.1`، `pillow==13.0.0`، `fonttools==4.67.0` (مثبّتة الإصدارات في `requirements.txt`) |

## التشغيل على جهاز جديد (الطريقة السهلة)

1. ثبّت Python 3.11 أو أحدث من <https://www.python.org/downloads/>،
   وفعّل خيار **Add python.exe to PATH** أثناء التثبيت (مشغّل `py` يُثبَّت تلقائيًا).
2. فُكّ ضغط الملف `ogrenci-not-takip-tasinabilir.zip` في أي مجلد تريده. لا مشكلة إن كان المسار
   يحتوي على مسافات أو أحرف تركية.
3. انقر نقرًا مزدوجًا على **`BASLAT.bat`**. يقوم الملف تلقائيًا بما يلي:
   - يبحث عن Python (أولًا `py -3` ثم `python`) ويتحقق من أن الإصدار 3.11 أو أحدث،
   - ينشئ بيئة افتراضية `.venv` داخل مجلد المشروع إذا لم تكن موجودة،
   - يثبّت المكتبات من `requirements.txt` (في المرة الأولى فقط أو عند تغيّر الملف)،
   - يفتح التطبيق بقاعدة البيانات التجريبية: `python main.py --demo`.
4. سجّل الدخول بأحد الحسابات التجريبية الموجودة في الجدول أدناه.

## التشغيل اليدوي (PowerShell)

```powershell
cd "مسار\ogrenci-not-takip"
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py --demo     # قاعدة البيانات التجريبية data\demo.db
.\.venv\Scripts\python.exe main.py --real     # قاعدة البيانات الحقيقية data\notlar.db
```

لتشغيل الاختبارات:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

## أين توجد البيانات؟

كل البيانات موجودة داخل مجلد المشروع، في المجلد `data\`:

| الملف | الوصف |
|---|---|
| `data\demo.db` | قاعدة البيانات التجريبية: 4 معلّمين، 30 طالبًا، 8 مقررات، والدرجات والرسائل |
| `data\notlar.db` | قاعدة البيانات الحقيقية، وفيها الحسابات التي أنشأتها بنفسك |
| `data\*-yedek*.db` | نسخ احتياطية تلقائية أو يدوية |

- يُحدَّد مسار قاعدة البيانات **بالنسبة لموقع `main.py`** وليس بالنسبة للمجلد الحالي، لذلك يعمل
  المشروع من أي مجلد وعلى أي جهاز. والمسار النسبي في `--db data\demo.db` يُحسب أيضًا من مجلد
  المشروع.
- الحسابات وكلمات المرور المشفّرة (PBKDF2-SHA256 مع salt عشوائي لكل حساب، محفوظ داخل
  القيمة المشفّرة نفسها) مخزّنة **داخل قاعدة البيانات فقط**. لا يوجد أي مفتاح أو salt مرتبط
  بالجهاز، ولا متغيرات بيئة، ولا ملفات خارج مجلد المشروع. لذلك تعمل نفس الحسابات بنفس كلمات
  المرور على أي جهاز.
- لنقل بياناتك لاحقًا يكفي نسخ مجلد `data\` كاملًا (يُفضَّل والتطبيق مغلق).

## الحسابات التجريبية (قاعدة البيانات `data\demo.db`)

كلمة المرور لجميع الحسابات التجريبية: **`1234`**

### المعلّمون

| اسم المستخدم | الاسم |
|---|---|
| `ogretmen1` | Ayşe Kaya |
| `ogretmen2` | Kemal Öztürk |
| `ogretmen3` | Selin Arslan |
| `ogretmen4` | Murat Şen |

### الطلاب

| اسم المستخدم | الاسم | رقم الطالب | السنة |
|---|---|---|---|
| `ogrenci1` | Elif Yılmaz | 2024001 | 2 |
| `ogrenci2` | Ahmet Demir | 2024002 | 2 |
| `ogrenci3` | Zeynep Kaya | 2024003 | 2 |
| `ogrenci4` | Mehmet Çelik | 2024004 | 2 |
| `ogrenci5` | Ayşe Şahin | 2024005 | 2 |
| `ogrenci6` | Burak Aydın | 2024006 | 2 |
| `ogrenci7` | Selin Yıldız | 2024007 | 2 |
| `ogrenci8` | Emre Koç | 2024008 | 2 |
| `ogrenci9` | Merve Kurt | 2024009 | 2 |
| `ogrenci10` | Can Özdemir | 2024010 | 2 |
| `ogrenci11` | İrem Aslan | 2024011 | 2 |
| `ogrenci12` | Oğuz Doğan | 2024012 | 2 |
| `ogrenci13` | Deniz Erdoğan | 2024013 | 2 |
| `ogrenci14` | Cem Polat | 2024014 | 2 |
| `ogrenci15` | Ece Güneş | 2024015 | 2 |
| `ogrenci16` | Kaan Tekin | 2023016 | 3 |
| `ogrenci17` | Buse Kılıç | 2023017 | 3 |
| `ogrenci18` | Yusuf Aksoy | 2023018 | 3 |
| `ogrenci19` | Esra Şimşek | 2023019 | 3 |
| `ogrenci20` | Arda Karaca | 2023020 | 3 |
| `ogrenci21` | Gizem Uçar | 2023021 | 3 |
| `ogrenci22` | Hakan Bulut | 2023022 | 3 |
| `ogrenci23` | Nazlı Ekinci | 2023023 | 3 |
| `ogrenci24` | Onur Taş | 2023024 | 3 |
| `ogrenci25` | Pınar Acar | 2023025 | 3 |
| `ogrenci26` | Serkan Yavuz | 2023026 | 3 |
| `ogrenci27` | Tuğba Özkan | 2023027 | 3 |
| `ogrenci28` | Umut Sarı | 2023028 | 3 |
| `ogrenci29` | Yağmur Ateş | 2023029 | 3 |
| `ogrenci30` | Barış Kara | 2023030 | 3 |

حسابات قاعدة البيانات الحقيقية (`data\notlar.db`) هي الحسابات التي أنشأتها بنفسك، وتبقى كلمات
مرورها كما هي.

## خيارات سطر الأوامر

| الأمر | الوظيفة |
|---|---|
| `python main.py` | بدون خيارات (ومنه زر التشغيل ▶ في VS Code): يفتح `data\demo.db` مع لوحة الحسابات التجريبية |
| `python main.py --real` | يفتح قاعدة البيانات الحقيقية `data\notlar.db` (بدون لوحة الحسابات) |
| `python main.py --demo` | يفتح `data\demo.db`، ويملؤها بالبيانات التجريبية إن كانت فارغة |
| `python main.py --demo --reset-demo` | يحذف قاعدة البيانات التجريبية ويعيد إنشاءها |
| `python main.py --db ملف.db` | يفتح ملف قاعدة بيانات آخر (المسار النسبي يُحسب من مجلد المشروع) |
| `python main.py --version` | يعرض رقم الإصدار |

## حل المشكلات

| المشكلة | الحل |
|---|---|
| تظهر رسالة «Python 3.11 veya uzeri bulunamadi» | ثبّت Python 3.11 أو أحدث من python.org مع تفعيل PATH، ثم شغّل `BASLAT.bat` مجددًا |
| يفتح متجر Microsoft عند كتابة `python` | عطّل «App execution aliases» الخاصة بـ python من إعدادات Windows، أو ثبّت Python من python.org |
| فشل تثبيت المكتبات | التثبيت الأول يحتاج إلى الإنترنت. تأكد من الاتصال، ثم شغّل `BASLAT.bat` مجددًا |
| خطأ `No module named tkinter` | أعد تثبيت Python من python.org مع تفعيل خيار «tcl/tk and IDLE» |
| تقارير PDF بخط مختلف | يستخدم التطبيق خطوط Windows ‏(Arial أو Segoe UI) من `C:\Windows\Fonts`، وإن لم يجدها يستخدم خطًا بديلًا |

</div>
