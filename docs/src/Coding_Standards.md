# 1. Amaç ve Kapsam

## 1.1 Amaç

Bu doküman, **Öğrenci Not Takip Sistemi (ONTS)** projesinde kullanılan kodlama standartlarını, kalite kurallarını ve geliştirme sürecindeki çalışma biçimini tanımlar. Amaç; projeye sonradan katılan bir geliştiricinin kodu hızlıca anlayabilmesini, ekip üyelerinin tutarlı biçimde üretim yapmasını ve otomatik araçlarla ölçülebilir bir kalite seviyesinin korunmasını sağlamaktır.

Doküman; yalnızca "nasıl yazılır" sorusuna değil, aynı zamanda yazılan kodun doğru olduğunun nasıl kontrol edileceği sorusuna da cevap verir. Bu nedenle her kural, uygulanabilir olduğu yerde bir araç, komut veya kod inceleme kontrolü ile ilişkilendirilmiştir.

## 1.2 Kapsam

Kurallar aşağıdaki dosya ve dizinlerin tamamını kapsar:

- `main.py` ve `app/` altındaki tüm üretim kodu,
- `tests/` altındaki tüm test kodu,
- `tools/` altındaki yardımcı betikler,
- `.github/workflows/` altındaki CI tanımları,
- Dokümantasyon ve diyagram kaynakları.

Kapsam dışı bırakılanlar: üçüncü taraf kütüphanelerin kaynak kodu, otomatik üretilen dosyalar (`__pycache__`, `.coverage`, geçici PDF/PNG çıktıları) ve kullanıcıya ait yerel veritabanı dosyaları.

# 2. Uygulama Ortamı ve Araçlar

## 2.1 Dil ve Çalışma Ortamı

| Öğe | Kural |
| --- | --- |
| Dil | Python 3.10 ve üzeri (geliştirme ve ölçüm: Python 3.15.1) |
| Kodlama | UTF-8, satır sonu LF (Windows'ta Git `core.autocrlf` ayarına bırakılır) |
| Arayüz | Tkinter / ttk (standart kütüphane) |
| Veritabanı | SQLite (`sqlite3` standart modülü) |
| Sanal ortam | `.venv` (depoya eklenmez) |
| Bağımlılık yönetimi | `requirements.txt` (çalışma), `requirements-dev.txt` (test/kalite) |

## 2.2 Kalite Araçları

| Araç | Sürüm | Görev | Başarısızlık eşiği |
| --- | --- | --- | --- |
| pytest | 9.2.0 | Birim ve entegrasyon testleri | Herhangi bir testin başarısız olması |
| pytest-cov / coverage | 7.17.0 | Satır kapsamı | İş katmanında %90'ın altı |
| flake8 | 7.5.0 | PEP 8, kullanılmayan import, karmaşıklık | Herhangi bir uyarı |
| pylint | 4.1.3 | Statik analiz ve tasarım limitleri | 9.00'ın altı |
| GitHub Actions | - | CI kalite kapısı | Adımlardan birinin kırmızı olması |

## 2.3 Yapılandırma Dosyaları

Kuralların bir kısmı kod incelemesine, önemli bir kısmı ise yapılandırma dosyalarına dayanır. Yapılandırmalar depo kökünde tutulur ve sürüm kontrolüne dahildir.

```ini
# .flake8
[flake8]
max-line-length = 100
max-complexity = 12
per-file-ignores =
    tests/*:E501
```

```ini
# .pylintrc (özet)
[FORMAT]
max-line-length = 100
indent-string = "    "

[DESIGN]
max-args = 8
max-attributes = 25
max-locals = 20
max-parents = 10
max-positional-arguments = 8
```

`# noqa` ve `# pylint: disable` kullanımı istisnadır; her kullanım gerekçesiyle birlikte kod incelemesinde onaylanmalıdır. Mevcut kodda `# pylint: disable` yalnızca iki yerde, işletim sistemine özgü klasör açma çağrılarında (`consider-using-with`) kullanılmıştır.

# 3. Proje Yapısı ve Dosya Adlandırma

## 3.1 Dizin Yapısı

Proje, katmanlı mimariyi yansıtacak şekilde düzenlenir. Yeni bir dosya eklenirken aşağıdaki yerleşim korunur:

```text
ogrenci-not-takip/
├── main.py                  # Yalnızca giriş noktası ve CLI ayrıştırma
├── app/
│   ├── config.py            # Sabitler ve yollar
│   ├── database.py          # Bağlantı, şema, transaction
│   ├── models.py            # Veri modelleri (dataclass)
│   ├── grading.py           # Saf hesaplama fonksiyonları
│   ├── validators.py        # Girdi doğrulama
│   ├── errors.py            # Hata hiyerarşisi
│   ├── demo_data.py         # Demo veri seti
│   ├── services/            # İş kuralları
│   └── ui/                  # Tkinter arayüzü
├── tests/                   # pytest testleri
├── tools/                   # İkon ve diyagram üretim betikleri
├── docs/                    # Dokümantasyon ve diyagramlar
└── .github/workflows/       # CI tanımı
```

## 3.2 Dosya Adlandırma

| Tür | Kural | Örnek |
| --- | --- | --- |
| Python modülü | `snake_case.py` | `grade_service.py` |
| Test modülü | `test_<konu>.py` | `test_grading.py` |
| Paket | `snake_case/` + `__init__.py` | `app/services/` |
| Doküman kaynağı | `PascalCase.md` veya `snake_case.md` | `Coding_Standards.md` |
| Diyagram kaynağı | `kebab-case.mmd` | `not-girisi-sira.mmd` |
| Üretilen çıktı | `snake_case_<tarih>.<uzantı>` | `karne_2026001_20261031.pdf` |

Dosya adlarında Türkçe karakter, boşluk ve büyük harf kullanılmaz. Bunun tek istisnası, teslimatta istenen doküman adlarıdır (`Coding_Standards.pdf` gibi).

# 4. Adlandırma Kuralları

## 4.1 Genel Kurallar

| Öğe | Kural | Örnek |
| --- | --- | --- |
| Değişken | `snake_case`, anlamlı | `weighted_average`, `student_id` |
| Fonksiyon / metot | `snake_case`, fiil ile başlar | `add_grade`, `compute_gpa` |
| Sınıf | `PascalCase`, tekil isim | `GradeService`, `StudentReport` |
| Sabit | `UPPER_SNAKE_CASE` | `PASS_THRESHOLD`, `DEFAULT_WEIGHTS` |
| Özel (private) üye | Tek alt çizgi öneki | `_validate`, `_reload` |
| Modül | `snake_case` | `report_service.py` |
| Tip değişkeni | `PascalCase` | `ModelT` |
| Test | `test_<davranış>` | `test_duplicate_exam_type_rejected` |

## 4.2 Anlamlılık ve Kısaltmalar

- Tek harfli isimler yalnızca döngü sayaçlarında (`i`, `j`) ve matematiksel formüllerde (`x`, `y`) kabul edilir.
- Yaygın kısaltmalar kullanılabilir: `db`, `id`, `ui`, `pdf`, `csv`, `gpa`, `no`.
- Türkçe alan adları veritabanında İngilizce tutulur; kullanıcıya gösterilen metin Türkçedir. Örneğin `student_no` alanı arayüzde "Öğrenci No" olarak görünür.
- Boolean değişkenler `is_`, `has_`, `can_` öneki alır: `is_passed`, `has_grades`.
- Koleksiyonlar çoğul adlandırılır: `students`, `courses`, `grades`.

## 4.3 Yasaklar

- `l`, `I`, `O` gibi tek harfli, okunması zor isimler kullanılmaz.
- Python anahtar kelimeleri gölgelenmez (`list`, `dict`, `id`, `type`).
- Aynı kapsamda anlam farkı belirsiz isimler (`data`, `info`, `temp`, `value2`) kullanılmaz.
- Türkçe ve İngilizce karışık isimlendirme yapılmaz (`ogrenciService` gibi).

# 5. Biçimlendirme Kuralları

## 5.1 Temel Biçim

- Girinti **4 boşluk**tur; sekme karakteri kullanılmaz.
- Satır uzunluğu en fazla **100** karakterdir. Test dosyalarında uzun veri satırları için `E501` istisnası tanımlıdır.
- Sınıflar arasında **2**, metotlar arasında **1** boş satır bırakılır.
- Mantıksal bloklar arasında en fazla 1 boş satır kullanılır.
- Dosya sonunda tek bir boş satır bulunur.
- Satır sonunda boşluk bırakılmaz.

## 5.2 İçe Aktarmalar (Imports)

İçe aktarmalar üç gruba ayrılır ve gruplar arasında bir boş satır bulunur:

1. Standart kütüphane (`argparse`, `sqlite3`, `pathlib`),
2. Üçüncü taraf kütüphaneler (`fpdf`, `pytest`),
3. Proje içi modüller (`app.config`, `app.database`).

```python
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fpdf import FPDF

from app import config
from app.errors import ValidationError
```

- `from module import *` kullanılmaz.
- Kullanılmayan import bırakılmaz; flake8 `F401` ile yakalar.
- Döngüsel import oluşturacak tasarımlardan kaçınılır; gerekirse `TYPE_CHECKING` kullanılır.

## 5.3 Tırnak, Virgül ve Parantezler

- Metinlerde çift tırnak (`"..."`) tercih edilir; iç içe metinlerde tek tırnak kullanılabilir.
- Çok satırlı koleksiyonlarda son elemandan sonra virgül bırakılır (trailing comma).
- Uzun fonksiyon çağrıları her argüman ayrı satırda olacak şekilde bölünür.

```python
ttk.Button(
    buttons,
    text="Güncelle",
    command=self._on_update,
).pack(side="left", padx=6)
```

## 5.4 Metin ve Türkçe Karakterler

- Kaynak dosyalar UTF-8'dir; Türkçe karakterler doğrudan yazılır (`Öğrenci`, `ağırlık`, `sınav`).
- Kullanıcıya gösterilen tüm metinler Türkçedir ve tam cümle kurar.
- Hata mesajları nokta ile biter; teknik ayrıntı yerine kullanıcıya eylemi söyler.
- Tarih gösterimi arayüzde `GG.AA.YYYY`, veritabanında ISO `YYYY-MM-DD` biçimindedir.

# 6. Docstring, Yorum ve Tip İpuçları

## 6.1 Docstring Kuralları

- Her modülün ilk satırında kısa bir modül docstring'i bulunur.
- Genel (public) sınıf ve fonksiyonlar docstring alır.
- Docstring Türkçe yazılır ve "ne yapar" sorusunu yanıtlar; parametreler karmaşıksa açıklanır.
- Üç çift tırnak kullanılır; tek satırlık docstring aynı satırda kapatılır.

```python
def weighted_average(items: Iterable[tuple[float, float]]) -> float | None:
    """(not, ağırlık) çiftlerinden ağırlıklı ortalama üretir.

    Ağırlık toplamı sıfır veya negatifse ``None`` döner.
    """
```

## 6.2 Yorum Kuralları

- Yorum, kodun **neden** öyle yazıldığını açıklar; ne yaptığını tekrar etmez.
- Kullanılmayan kod yorum satırına alınmaz; silinir (sürüm kontrolü zaten saklar).
- `TODO` ve `FIXME` notları sahiplik ve tarih içerir: `# TODO(elif, 2026-11): dönem filtresi`.
- Arayüz kodunda bölüm ayırıcıları kısa tutulur:

```python
# ------------------------------------------------------------- doğrulama
```

## 6.3 Tip İpuçları

- Tüm genel fonksiyon ve metotlarda parametre ve dönüş tipleri belirtilir.
- Modern birleşim sözdizimi kullanılır: `int | None`, `list[Student]`.
- Koleksiyonlar için `collections.abc` tipleri tercih edilir: `Iterable`, `Sequence`.
- `Any` kullanımından kaçınılır; zorunluysa gerekçesi yorumla belirtilir.

# 7. Fonksiyon ve Sınıf Tasarımı

## 7.1 Fonksiyonlar

- Her fonksiyon tek bir iş yapar (Single Responsibility).
- Fonksiyon uzunluğu mümkünse 40 satırı geçmez; aşılırsa parçalara ayrılır.
- Parametre sayısı en fazla 8'dir (pylint `max-args`).
- Varsayılan parametre olarak değiştirilebilir nesne (`[]`, `{}`) kullanılmaz; `None` + içeride oluşturma tercih edilir.
- Hesaplama mantığı (özellikle `grading.py`) veritabanından bağımsız **saf fonksiyon** olarak yazılır. Aynı girdi her zaman aynı çıktıyı üretir; yan etki oluşturmaz.
- Erken dönüş (early return) tercih edilir; iç içe `if` derinliği 3'ü geçmez.

## 7.2 Sınıflar

- Sınıflar tek bir sorumluluk taşır: `StudentService` yalnızca öğrenci iş kurallarını, `ReportService` yalnızca çıktı üretimini yönetir.
- Veri taşıyan sınıflar `@dataclass` olarak tanımlanır; mümkün olduğunda `frozen=True` kullanılır.
- Servis sınıfları bağımlılıklarını kurucuda alır (constructor injection): `GradeService(db)`.
- Kalıtım yerine kompozisyon tercih edilir. Kalıtım yalnızca gerçek bir "is-a" ilişkisi varsa kullanılır (ör. `ReportPDF(FPDF)`).
- Sınıf öznitelik sayısı 25'i, yerel değişken sayısı 20'yi geçmez.

## 7.3 Katman Sorumlulukları

| Katman | Sorumluluk | Yapmaması gereken |
| --- | --- | --- |
| `app/ui` | Widget, kullanıcı etkileşimi, mesaj gösterimi | SQL yazmak, iş kuralı hesaplamak |
| `app/services` | İş kuralları, doğrulama, rapor üretimi | Tkinter widget'ı oluşturmak |
| `app/database` | Bağlantı, şema, transaction | İş kuralı bilmek |
| `app/grading` | Saf hesaplama | Veritabanına erişmek |
| `app/models` | Veri temsili | İş kuralı veya G/Ç yapmak |

Bağımlılık yönü tek yönlüdür: `ui → services → database`. Alt katman, üst katmanı import etmez.

# 8. Hata Yönetimi

## 8.1 Hata Hiyerarşisi

Uygulamaya özgü tüm hatalar `AppError` sınıfından türer:

```text
AppError
├── ValidationError   # Kullanıcı girdisi veya iş kuralı ihlali
└── NotFoundError     # Kayıt bulunamadı
```

- Servis katmanı teknik ayrıntıyı (SQL hatası, `sqlite3.IntegrityError`) yakalar ve anlamlı bir `ValidationError`/`NotFoundError` üretir.
- Arayüz katmanı yalnızca `AppError` yakalar ve `messagebox` ile gösterir.
- Beklenmeyen hatalar gizlenmez; program çökerse iz kaydı (traceback) korunur.

## 8.2 Kurallar

- Çıplak `except:` kullanılmaz. En azından `except Exception as exc:` yazılır ve yeniden fırlatılır veya dönüştürülür.
- Hata dönüştürürken `raise ... from exc` kullanılır; kök neden kaybolmaz.
- `pass` ile sessizce yutulan istisna kabul edilmez.
- Kaynaklar `with` bloğu veya `try/finally` ile serbest bırakılır.
- Veritabanı işlemleri transaction içinde yapılır; hata durumunda `rollback` otomatik gerçekleşir.

```python
try:
    new_id = self.db.execute(sql, params)
except sqlite3.IntegrityError as exc:
    raise ValidationError("Bu öğrenci numarası zaten kayıtlı.") from exc
```

## 8.3 Kullanıcı Mesajları

| Durum | Mesaj biçimi | Örnek |
| --- | --- | --- |
| Zorunlu alan | `<Alan> zorunludur.` | `Ad zorunludur.` |
| Aralık hatası | `<Alan> <min> ile <max> arasında olmalıdır.` | `Puan 0 ile 100 arasında olmalıdır.` |
| Tekillik | `Bu <nesne> zaten kayıtlı.` | `Bu ders kodu zaten kayıtlı.` |
| Bulunamadı | `<Nesne> bulunamadı.` | `Öğrenci bulunamadı.` |
| Onay | `... Devam edilsin mi?` | Silme onayı |

# 9. Veritabanı ve SQL Kuralları

## 9.1 Sorgu Güvenliği

- Tüm sorgular **parametreli** yazılır; kullanıcı girdisi asla SQL metnine doğrudan eklenmez.
- Dinamik `ORDER BY` veya tablo adı gerekiyorsa yalnızca beyaz listeden seçilir.
- `SELECT *` yalnızca modelin tüm alanları gerçekten gerekiyorsa kullanılır; rapor sorgularında alanlar açıkça yazılır.

```python
rows = self.db.query(
    "SELECT * FROM students WHERE student_no LIKE ? ORDER BY student_no",
    (f"%{text}%",),
)
```

## 9.2 Şema ve Bütünlük

- Birincil anahtarlar `INTEGER PRIMARY KEY AUTOINCREMENT` olarak tanımlanır.
- İş anahtarları `UNIQUE` kısıtı alır: `students.student_no`, `courses.code`, `grades(student_id, course_id, exam_type)`.
- Aralık kısıtları veritabanında da tanımlanır: `score BETWEEN 0 AND 100`, `credit BETWEEN 1 AND 10`, `weight > 0`.
- Yabancı anahtarlar `REFERENCES ... ON DELETE CASCADE` ile tanımlanır ve her bağlantıda `PRAGMA foreign_keys = ON` çalıştırılır.
- Sık sorgulanan yabancı anahtar alanlarına indeks eklenir (`idx_grades_student`, `idx_grades_course`).
- Şema değişiklikleri `SCHEMA` sabitinde yapılır ve `CREATE TABLE IF NOT EXISTS` ile geriye uyumlu tutulur. Kırıcı değişikliklerde migration betiği ve sürüm notu zorunludur.

## 9.3 Transaction Kuralı

- Birden fazla satırı etkileyen işlemler tek transaction'da yapılır.
- `Database.cursor()` bağlam yöneticisi başarıda `commit`, hatada `rollback` uygular.
- Uzun süren okuma işlemleri transaction içinde tutulmaz.

# 10. Arayüz (UI) Kodlama Kuralları

- Arayüz katmanı yalnızca sunum yapar; iş kuralı içermez. Hesaplama servislerden alınır.
- Tüm renk, font ve stil tanımları `app/ui/common.py` içinde merkezîleştirilir. Widget içinde sabit renk kodu yazılmaz.
- Sekmeler `ttk.Frame` tabanlıdır ve ortak `make_tree`, `clear_tree`, `show_error` yardımcılarını kullanır.
- Kullanıcıya gösterilen tüm etiketler Türkçe ve kısa fiil cümleleridir: "Ekle", "Güncelle", "Sil", "Formu Temizle".
- Yıkıcı işlemler (silme) için `messagebox.askyesno` ile onay alınır ve sonuç geri alınamaz olduğu belirtilir.
- Başarılı işlemler durum çubuğunda (`set_status`) bildirilir; hatalar `messagebox.showerror` ile gösterilir.
- Arayüz iş parçacığında uzun süren işlem yapılmaz; rapor üretimi kısa tutulur, ileride büyük veri için arka plan iş parçacığı planlanmıştır.
- Klavye erişimi gözetilir: `Tab` sırası doğal, `F5` yenileme, `Enter` varsayılan eylem.
- Pencere minimum boyutu `1000x660` olarak korunur; yerleşim `grid` ağırlıklarıyla esnek yapılır.

# 11. Test Kodlama Standartları

## 11.1 Genel Kurallar

- Testler `pytest` ile yazılır; `unittest` sınıfı zorunlu değildir.
- Test dosyası adı `test_<modül>.py`, test fonksiyonu adı `test_<davranış>` biçimindedir.
- Her test tek bir davranışı doğrular; birden fazla `assert` aynı davranışın parçaları olabilir.
- Testler birbirinden bağımsızdır; sıraya veya paylaşılan duruma güvenmez.
- Her test kendi geçici veritabanını kullanır (`tmp_path`); üretim veritabanına dokunulmaz.
- Testler ağ erişimi, gerçek kullanıcı dosyası veya sistem saati gibi dış etkenlere bağlı olmaz. Tarih gerektiğinde sabit değer verilir.
- Beklenen hata `pytest.raises` ile ve mesaj içeriği kontrol edilerek doğrulanır.

## 11.2 Yapı (Arrange–Act–Assert)

```python
def test_duplicate_student_number_rejected(student_service):
    # Arrange
    student_service.add("2026001", "Elif", "Yılmaz")

    # Act / Assert
    with pytest.raises(ValidationError, match="zaten kayıtlı"):
        student_service.add("2026001", "Ahmet", "Demir")
```

## 11.3 Parametrik Testler

Sınır değerleri ve hata varyasyonları `@pytest.mark.parametrize` ile yazılır. Böylece her varyasyon ayrı test olarak raporlanır ve kapsam artar.

```python
@pytest.mark.parametrize(
    ("score", "expected"),
    [(100, "AA"), (90, "AA"), (89.99, "BA"), (60, "DD"), (59.99, "FD")],
)
def test_letter_grade_boundaries(score, expected):
    assert letter_grade(score) == expected
```

## 11.4 Kapsam ve İsimlendirme

- İş katmanı için satır kapsamı hedefi **≥ %90**'dır; mevcut ölçüm **%97**'dir.
- Arayüz (`app/ui`) otomatik kapsam dışıdır; ayrıca duman testiyle doğrulanır.
- Test adları Türkçe davranışı İngilizce anahtar kelimelerle anlatır: `test_invalid_credit_rejected`, `test_course_delete_cascades_grades`.
- Test verisi gerçekçi ama küçüktür; her test yalnızca ihtiyaç duyduğu kaydı oluşturur.

# 12. Sürüm Kontrolü ve Commit Kuralları

## 12.1 Dal Stratejisi

| Dal | Amaç |
| --- | --- |
| `main` | Her zaman çalışan, CI'dan geçmiş sürüm |
| `feature/<kısa-ad>` | Yeni özellik |
| `fix/<kısa-ad>` | Hata düzeltmesi |
| `docs/<kısa-ad>` | Dokümantasyon değişikliği |

- `main` dalına doğrudan commit atılmaz; değişiklikler pull request ile alınır.
- Pull request en az bir ekip üyesi tarafından incelenir.
- CI kırmızıysa birleştirme yapılmaz.

## 12.2 Commit Mesajı (Conventional Commits)

```text
<tip>(<kapsam>): <kısa açıklama>

<gövde: ne ve neden>
<alt bilgi: kırıcı değişiklik, kapatılan konu>
```

| Tip | Kullanım |
| --- | --- |
| `feat` | Yeni özellik |
| `fix` | Hata düzeltmesi |
| `test` | Test ekleme/düzeltme |
| `docs` | Dokümantasyon |
| `refactor` | Davranış değiştirmeyen iyileştirme |
| `style` | Biçimlendirme |
| `chore` | Yapılandırma, bağımlılık |
| `ci` | CI değişikliği |

Örnekler:

```text
feat(grades): varsayılan sınav ağırlıklarını uygula
fix(reports): PDF raporunda Türkçe karakterleri koru
test(grading): harf notu sınır değerlerini kapsa
docs(readme): kurulum adımlarını güncelle
```

## 12.3 Sürüm Etiketleme

- Sürümler `MAJOR.MINOR.PATCH` biçimindedir (`1.0.0`).
- Teslim sürümleri `v1.0.0` etiketiyle işaretlenir.
- `CHANGELOG.md` her sürümde güncellenir (planlanan iyileştirme).

# 13. Dokümantasyon Standartları

- Her dokümanın kapağında proje adı, doküman adı ve tarih bulunur.
- Başlıklar numaralıdır; en fazla 3 seviye kullanılır (`1.`, `1.1`, `1.1.1`).
- Tablolar tercih edilir; uzun paragraflar madde işaretleriyle bölünür.
- Kod örnekleri kopyalanabilir ve çalıştırılabilir olmalıdır.
- Ekran görüntüleri `docs/ekran-*.png`, diyagramlar `docs/diagrams/*.png` altında tutulur.
- Dokümanlar Markdown kaynağından üretilir; PDF çıktısı `docs/deliverables/` altına yazılır.

# 14. Kod İnceleme Kontrol Listesi

Her pull request aşağıdaki listeye göre incelenir. İşaretlenmeyen madde varsa birleştirme yapılmaz.

| # | Kontrol | Kontrol ölçütü |
| --- | --- | --- |
| 1 | Değişiklik tek bir amaca hizmet ediyor mu? | PR açıklaması ve diff kapsamı |
| 2 | Katman sınırları korunmuş mu? | UI içinde SQL veya iş kuralı yok |
| 3 | Adlandırma kurallarına uyulmuş mu? | flake8 + gözden geçirme |
| 4 | Hata yolları ele alınmış mı? | `AppError` dönüşümü, rollback |
| 5 | Kullanıcı mesajları Türkçe ve anlaşılır mı? | Arayüz metinleri |
| 6 | Yeni davranış için test eklenmiş mi? | `tests/` diff'i |
| 7 | Mevcut testler bozulmamış mı? | CI yeşil |
| 8 | Kapsam düşmüş mü? | `--cov` raporu |
| 9 | Docstring ve tip ipuçları güncel mi? | pylint |
| 10 | Dokümantasyon etkilenmiş mi? | README / docs diff'i |
| 11 | Gizli bilgi, parola veya yerel yol commit'e girmiş mi? | diff taraması |
| 12 | Commit mesajı Conventional Commits'e uygun mu? | `git log` |

# 15. Uyumluluk ve Ölçüm

## 15.1 Ölçülen Sonuçlar

Ölçüm tarihi **31.10.2026**, ortam **Windows 11 / Python 3.15.1**:

| Metrik | Sonuç | Durum |
| --- | --- | --- |
| Test sayısı | 106 geçti, 0 başarısız | Uyumlu |
| İş katmanı kapsamı (`app/ui` hariç) | %97 (606 satırdan 588'i) | Uyumlu |
| flake8 | 0 uyarı | Uyumlu |
| pylint | 10.00 / 10 | Uyumlu |
| Maksimum satır uzunluğu | 100 | Uyumlu |
| Maksimum karmaşıklık | 12 | Uyumlu |

## 15.2 Doğrulama Komutları

```powershell
python -m pytest -q
python -m pytest --cov=app --cov-report=term-missing
python -m flake8 app tests main.py
python -m pylint app main.py
```

Bu komutlar `.github/workflows/ci.yml` içinde her push ve pull request'te otomatik çalıştırılır. Adımlardan biri başarısız olursa iş akışı kırmızı olur ve birleştirme engellenir.

## 15.3 İstisnalar ve Gerekçeleri

| İstisna | Gerekçe | Onay |
| --- | --- | --- |
| `app/ui/*` kapsam dışı | Tkinter görüntü sunucusu gerektirir; CI başsız çalışır | Test Results dokümanında açıklandı |
| `tests/*:E501` | Parametrik test veri satırları uzun | `.flake8` |
| `duplicate-code` kapalı | CRUD blokları servisler arasında bilinçli ayrık | `.pylintrc` |
| `missing-*-docstring` kapalı | İç yardımcı fonksiyonlarda gürültü | `.pylintrc` |
