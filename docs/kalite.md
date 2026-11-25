# Kod Kalitesi ve Test Raporu

Ölçüm tarihi: **31.10.2026** · Ortam: **Windows / Python 3.15.1**

| Araç | Sürüm | Amaç |
| --- | --- | --- |
| pytest | 9.2.0 | Birim testleri |
| pytest-cov / coverage | 7.17.0 | Satır kapsamı |
| flake8 | 7.5.0 | PEP 8, kullanılmayan import, karmaşıklık |
| pylint | 4.1.3 | Statik analiz ve kalite puanı |

## Özet Sonuçlar

| Metrik | Sonuç | Durum |
| --- | --- | --- |
| Test sayısı | **106 geçti, 0 başarısız** | ✅ |
| İş katmanı kapsamı (`app/ui` hariç) | **%97** (606 satırdan 588'i) | ✅ |
| flake8 | **0 uyarı** | ✅ |
| pylint | **10.00 / 10** | ✅ |
| Maksimum satır uzunluğu | 100 karakter | ✅ |
| Maksimum karmaşıklık (`max-complexity`) | 12 | ✅ |

## Kapsam Detayı

Komut:

```powershell
python -m pytest --cov=app --cov-report=term-missing
```

| Dosya | Kapsam |
| --- | --- |
| `app/database.py` | %98 |
| `app/grading.py` | %95 |
| `app/validators.py` | %96 |
| `app/services/course_service.py` | %91 |
| `app/services/grade_service.py` | %96 |
| `app/services/report_service.py` | %97 |
| `app/services/student_service.py` | %100 |
| `app/models.py`, `app/config.py`, `app/errors.py`, `app/demo_data.py` | %100 |
| **Toplam (arayüz hariç)** | **%97** |

### Arayüz neden kapsam dışı?

Tkinter widget'ları görüntü sunucusu gerektirir; `pytest` GitHub Actions'ın Ubuntu
runner'ında başsız (headless) çalıştığı için arayüz testleri CI'da kırılır. Bu nedenle:

- `app/ui/*` dosyaları `.coveragerc` içinde kapsam dışı bırakıldı.
- Arayüz ayrıca elle ve otomatik bir duman testiyle (`AppWindow` oluşturup dört sekmeyi
  gezme) doğrulandı.
- Yol haritasında `pytest-xvfb` ile arayüz testleri eklemek var.

## flake8 Yapılandırması

`.flake8`:

```ini
[flake8]
max-line-length = 100
max-complexity = 12
per-file-ignores =
    tests/*:E501
```

Kodda `# noqa` kullanılmamıştır; tüm uyarılar gerçek düzeltmelerle giderilmiştir.

## pylint Yapılandırması

`.pylintrc` içinde yalnızca projeye uygun, gürültü üreten kontroller kapatıldı:

- `missing-*-docstring` — her iç fonksiyon için docstring zorunluluğu kaldırıldı.
- `too-few-public-methods` — veri modeli sınıfları için.
- `duplicate-code` — benzer CRUD blokları servisler arasında bilinçli olarak ayrık tutuldu.
- `fixme` — yol haritası notları.

Tasarım limitleri (`.pylintrc`):

```ini
[DESIGN]
max-args = 8
max-attributes = 25
max-locals = 20
max-parents = 10
max-positional-arguments = 8
```

## Test Dağılımı

| Test dosyası | Kapsam |
| --- | --- |
| `tests/test_grading.py` | Ağırlıklı ortalama, harf notu sınırları, GNO, biçimlendirme |
| `tests/test_database.py` | Şema, foreign key, cascade, transaction rollback |
| `tests/test_students.py` | CRUD, arama, benzersizlik, doğrulama |
| `tests/test_courses.py` | CRUD, kredi/kod doğrulama, arama |
| `tests/test_grades.py` | Not CRUD, varsayılan ağırlık, karne, sınıf özeti |
| `tests/test_reports.py` | CSV içeriği, PDF ikili çıktısı, önizlemeler |
| `tests/test_demo_data.py` | Demo veri yükleme ve tekrar çalıştırılabilirlik |

## CI Kapısı

`.github/workflows/ci.yml` her `push` ve `pull_request` olayında şunları çalıştırır:

```powershell
python -m pytest --cov=app --cov-report=term-missing
python -m flake8 app tests main.py
python -m pylint app main.py
```

Adımlardan biri başarısız olursa iş akışı kırmızı olur; `main` dalına kalite kapısı
olmadan değişiklik alınmaması önerilir.
