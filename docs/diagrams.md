# Diyagramlar

Tüm diyagramlar [Mermaid](https://mermaid.js.org/) ile yazılmıştır. GitHub, GitLab ve
Mermaid eklentisi kurulu VS Code'da doğrudan görüntülenir. draw.io'da düzenlemek için
`docs/mermaid/` altındaki `.mmd` dosyalarını **Arrange → Insert → Advanced → Mermaid**
menüsünden içe aktarabilirsiniz.

## 1. ER Diyagramı

Veritabanı şeması ve ilişkiler:

```mermaid
erDiagram
    STUDENTS ||--o{ GRADES : "not alır"
    COURSES ||--o{ GRADES : "not içerir"

    STUDENTS {
        INTEGER id PK
        TEXT student_no UK "benzersiz öğrenci numarası"
        TEXT first_name
        TEXT last_name
        TEXT department
        TEXT email
        TEXT created_at
    }

    COURSES {
        INTEGER id PK
        TEXT code UK "benzersiz ders kodu"
        TEXT name
        INTEGER credit "1-10"
        TEXT instructor
        TEXT semester
    }

    GRADES {
        INTEGER id PK
        INTEGER student_id FK
        INTEGER course_id FK
        TEXT exam_type "Vize, Final, Ödev, Proje"
        REAL score "0-100"
        REAL weight "ağırlık"
        TEXT exam_date
    }
```

- Bir öğrenci çok sayıda nota, bir ders çok sayıda nota sahiptir.
- `(student_id, course_id, exam_type)` üçlüsü benzersizdir; aynı sınav türü iki kez girilemez.
- Silme işlemleri `ON DELETE CASCADE` ile notlara yansır.

## 2. Kullanım Durumu Diyagramı

```mermaid
flowchart LR
    hoca(("Öğretim Görevlisi"))

    subgraph sistem["Öğrenci Not Takip Sistemi"]
        uc1["Öğrenci kaydı yönet"]
        uc2["Ders kaydı yönet"]
        uc3["Not gir / güncelle / sil"]
        uc4["Karne ve GNO görüntüle"]
        uc5["PDF / CSV rapor al"]
        uc6["Veritabanını yedekle"]
    end

    hoca --> uc1
    hoca --> uc2
    hoca --> uc3
    hoca --> uc4
    hoca --> uc5
    hoca --> uc6

    uc3 -.->|"içerir"| uc4
    uc4 -.->|"besler"| uc5
```

## 3. Mimari Diyagram

Katmanlı mimari; bağımlılıklar tek yönlüdür (`ui → services → database`).

```mermaid
flowchart TB
    subgraph sunum["Sunum Katmanı - Tkinter"]
        t1["Öğrenciler sekmesi"]
        t2["Dersler sekmesi"]
        t3["Notlar sekmesi"]
        t4["Raporlar sekmesi"]
    end

    subgraph is["İş Katmanı - app/services"]
        s1["StudentService"]
        s2["CourseService"]
        s3["GradeService"]
        s4["ReportService"]
        g["grading.py<br/>saf hesaplama fonksiyonları"]
        v["validators.py<br/>girdi doğrulama"]
    end

    db[("SQLite<br/>data/notlar.db")]
    out["Çıktılar<br/>PDF (fpdf2) · CSV (csv)"]
    test["pytest · flake8 · pylint"]

    t1 --> s1
    t2 --> s2
    t3 --> s3
    t4 --> s4

    s1 --> db
    s2 --> db
    s3 --> db
    s4 --> db

    s1 --> v
    s2 --> v
    s3 --> v
    s3 --> g
    s4 --> g
    s4 --> out

    test -.->|"doğrular"| is
```

## 4. Not Girişi Sıra Diyagramı

```mermaid
sequenceDiagram
    autonumber
    actor H as Kullanıcı
    participant UI as GradesTab
    participant S as GradeService
    participant V as validators
    participant DB as SQLite

    H->>UI: Öğrenci, ders, sınav türü, puan ve ağırlık girer
    UI->>S: add(student_id, course_id, exam_type, score, weight, date)
    S->>S: Öğrenci ve ders var mı?
    S->>V: parse_decimal / parse_date
    V-->>S: Doğrulanmış değerler
    alt Aynı sınav türü zaten var
        S-->>UI: ValidationError
        UI-->>H: Hata mesajı gösterilir
    else Kayıt uygun
        S->>DB: INSERT INTO grades
        DB-->>S: grade_id
        S-->>UI: Grade nesnesi
        UI->>UI: Notları ve özeti yenile
        UI-->>H: "Not eklendi" + güncel GNO
    end
```

## 5. Not Hesaplama Akışı

```mermaid
flowchart LR
    a["Ham notlar<br/>(puan, ağırlık)"] --> b["Ders ağırlıklı ortalaması<br/>Σ(puan×ağırlık) / Σağırlık"]
    b --> c["Harf notu ve katsayı<br/>AA ... FF"]
    c --> d["GNO<br/>Σ(katsayı×kredi) / Σkredi"]
    b --> e{"Ortalama ≥ 60?"}
    e -->|"Evet"| f["Ders: Geçti"]
    e -->|"Hayır"| g["Ders: Kaldı"]
    c --> h["Karne / PDF / CSV"]
    d --> h
```

## Katman Sorumlulukları

| Katman | Dosyalar | Sorumluluk |
| --- | --- | --- |
| Sunum | `app/ui/*` | Widget'lar, kullanıcı etkileşimi, hata mesajları |
| İş | `app/services/*`, `app/grading.py`, `app/validators.py` | İş kuralları, doğrulama, hesaplama, rapor üretimi |
| Veri | `app/database.py`, `app/models.py` | Bağlantı, şema, transaction, satır modelleri |
| Altyapı | `app/config.py`, `app/errors.py`, `app/demo_data.py` | Sabitler, hata türleri, demo veri |

## Renk / Biçim Notları

- Diyagramlarda Türkçe karakterler doğrudan kullanılabilir.
- draw.io içe aktarımında Mermaid'in desteklemediği özel biçimlendirmeler (gölge, ikon)
  kaybolabilir; kutu ve oklar korunur.
