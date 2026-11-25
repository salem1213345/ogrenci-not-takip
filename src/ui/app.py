"""Tkinter arayuzu (sunum katmani). Is mantigi servis katmanindadir."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.models.entities import Course, Student
from src.repositories.repos import DuplicateError
from src.services.app_services import (CourseService, EnrollmentService,
                                       GradeService, StudentService)
from src.services.exporter import ReportExporter

TERM_DEFAULT = "2026-Güz"


def fmt(v):
    return "" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v))


def parse_score(text):
    """Bos metin -> None, sayi -> float; aksi halde ValueError."""
    text = text.strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError("Not sayısal olmalıdır.") from exc


class App(tk.Tk):
    def __init__(self, conn):
        super().__init__()
        self.title("Öğrenci Not Takip Sistemi")
        self.geometry("900x560")
        self.students = StudentService(conn)
        self.courses = CourseService(conn)
        self.enrollments = EnrollmentService(conn)
        self.grades = GradeService(conn)
        self.exporter = ReportExporter(self.students, self.courses,
                                       self.enrollments, self.grades)
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.student_tab = StudentTab(nb, self)
        self.course_tab = CourseTab(nb, self)
        self.grade_tab = GradeTab(nb, self)
        self.report_tab = ReportTab(nb, self)
        for text, tab in (("Öğrenciler", self.student_tab),
                          ("Dersler ve Kayıt", self.course_tab),
                          ("Not Girişi", self.grade_tab),
                          ("Raporlar", self.report_tab)):
            nb.add(tab, text=text)
        nb.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())

    def refresh_all(self):
        for tab in (self.student_tab, self.course_tab, self.grade_tab,
                    self.report_tab):
            tab.refresh()

    def run_action(self, func):
        """Servis cagrisini hata mesajlariyla sarar; basari durumunda True."""
        try:
            func()
            return True
        except (ValueError, DuplicateError) as exc:
            messagebox.showwarning("Uyarı", str(exc))
        except OSError as exc:
            messagebox.showerror("Dosya hatası", f"Dosya yazılamadı: {exc}")
        return False


def make_table(parent, columns, height=12):
    tree = ttk.Treeview(parent, columns=[c[0] for c in columns],
                        show="headings", height=height)
    for key, title, width in columns:
        tree.heading(key, text=title)
        tree.column(key, width=width, anchor="w")
    return tree


class StudentTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        top = ttk.Frame(self)
        top.pack(fill="x", pady=4)
        self.q = tk.StringVar()
        ttk.Entry(top, textvariable=self.q).pack(side="left", padx=4)
        ttk.Button(top, text="Ara", command=self.refresh).pack(side="left")
        ttk.Button(top, text="Sil", command=self.delete).pack(side="right", padx=4)
        ttk.Button(top, text="Güncelle", command=self.update).pack(side="right")
        ttk.Button(top, text="Ekle", command=self.add).pack(side="right", padx=4)
        self.tree = make_table(self, [("id", "ID", 40), ("no", "Numara", 110),
                                      ("first", "Ad", 150), ("last", "Soyad", 150),
                                      ("email", "E-posta", 250)])
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        form = ttk.Frame(self)
        form.pack(fill="x", pady=6)
        self.vars = {k: tk.StringVar() for k in ("no", "first", "last", "email")}
        for i, (k, label) in enumerate((("no", "Numara *"), ("first", "Ad *"),
                                        ("last", "Soyad *"), ("email", "E-posta"))):
            ttk.Label(form, text=label).grid(row=0, column=i * 2, padx=2)
            ttk.Entry(form, textvariable=self.vars[k], width=16).grid(
                row=0, column=i * 2 + 1, padx=2)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for s in self.app.students.search(self.q.get()):
            self.tree.insert("", "end", iid=str(s.id), values=(
                s.id, s.student_no, s.first_name, s.last_name, s.email or ""))

    def _student_from_form(self, sid=None):
        v = {k: x.get() for k, x in self.vars.items()}
        return Student(v["no"], v["first"], v["last"], v["email"] or None, sid)

    def selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def on_select(self, _e):
        sid = self.selected_id()
        if sid is not None:
            vals = self.tree.item(str(sid))["values"]
            for k, val in zip(("no", "first", "last", "email"), vals[1:]):
                self.vars[k].set(val)

    def add(self):
        if self.app.run_action(lambda: self.app.students.add(self._student_from_form())):
            self.refresh()

    def update(self):
        sid = self.selected_id()
        if sid is None:
            return messagebox.showinfo("Bilgi", "Önce bir öğrenci seçin.")
        if self.app.run_action(lambda: self.app.students.update(self._student_from_form(sid))):
            self.refresh()

    def delete(self):
        sid = self.selected_id()
        if sid is None:
            return messagebox.showinfo("Bilgi", "Önce bir öğrenci seçin.")
        if messagebox.askyesno("Onay", "Öğrenci ve tüm kayıt/notları silinecek. Emin misiniz?"):
            self.app.students.delete(sid)
            self.refresh()


class CourseTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.course_map, self.student_map = {}, {}
        left = ttk.LabelFrame(self, text="Ders tanımla")
        left.pack(side="left", fill="y", padx=6, pady=6)
        self.v = {k: tk.StringVar(value=d) for k, d in
                  (("code", ""), ("name", ""), ("credit", "3"),
                   ("mid", "40"), ("fin", "60"))}
        for label, key in (("Kod *", "code"), ("Ad *", "name"), ("Kredi *", "credit"),
                           ("Vize %", "mid"), ("Final %", "fin")):
            ttk.Label(left, text=label).pack(anchor="w")
            ttk.Entry(left, textvariable=self.v[key]).pack(fill="x")
        ttk.Button(left, text="Ders Ekle", command=self.add_course).pack(pady=4)
        ttk.Button(left, text="Seçili Dersi Sil", command=self.delete_course).pack()
        right = ttk.LabelFrame(self, text="Derse kayıt")
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.course_cb = ttk.Combobox(right, state="readonly")
        self.student_cb = ttk.Combobox(right, state="readonly")
        self.term = tk.StringVar(value=TERM_DEFAULT)
        for label, w in (("Ders", self.course_cb), ("Öğrenci", self.student_cb)):
            ttk.Label(right, text=label).pack(anchor="w")
            w.pack(fill="x")
        ttk.Label(right, text="Dönem").pack(anchor="w")
        ttk.Entry(right, textvariable=self.term).pack(fill="x")
        ttk.Button(right, text="Kaydet", command=self.enroll).pack(pady=4)
        self.tree = make_table(right, [("no", "Numara", 90), ("name", "Ad Soyad", 180),
                                       ("term", "Dönem", 90)], height=8)
        self.tree.pack(fill="both", expand=True)
        ttk.Button(right, text="Seçili Kaydı Sil", command=self.drop).pack(pady=4)
        self.course_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_enrolled())

    def refresh(self):
        courses = self.app.courses.list_all()
        self.course_map = {f"{c.code} - {c.name}": c for c in courses}
        self.course_cb["values"] = list(self.course_map)
        studs = self.app.students.list_all()
        self.student_map = {f"{s.student_no} {s.full_name()}": s for s in studs}
        self.student_cb["values"] = list(self.student_map)
        self.refresh_enrolled()

    def refresh_enrolled(self):
        self.tree.delete(*self.tree.get_children())
        c = self.course_map.get(self.course_cb.get())
        if c:
            for eid, term, s in self.app.enrollments.list_by_course(c.id):
                self.tree.insert("", "end", iid=str(eid),
                                 values=(s.student_no, s.full_name(), term))

    def add_course(self):
        def action():
            c = Course(self.v["code"].get(), self.v["name"].get(),
                       int(self.v["credit"].get() or 0),
                       float(self.v["mid"].get()), float(self.v["fin"].get()))
            self.app.courses.add(c)
        if self.app.run_action(action):
            self.refresh()

    def delete_course(self):
        c = self.course_map.get(self.course_cb.get())
        if c and messagebox.askyesno("Onay", "Ders ve ilgili kayıtlar silinecek. Emin misiniz?"):
            self.app.courses.delete(c.id)
            self.course_cb.set("")
            self.refresh()

    def enroll(self):
        c = self.course_map.get(self.course_cb.get())
        s = self.student_map.get(self.student_cb.get())
        if not (c and s):
            return messagebox.showinfo("Bilgi", "Ders ve öğrenci seçin.")
        if self.app.run_action(lambda: self.app.enrollments.enroll(s.id, c.id, self.term.get())):
            self.refresh_enrolled()

    def drop(self):
        sel = self.tree.selection()
        if sel:
            self.app.enrollments.drop(int(sel[0]))
            self.refresh_enrolled()


class GradeTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.course_map = {}
        top = ttk.Frame(self)
        top.pack(fill="x", pady=4)
        ttk.Label(top, text="Ders:").pack(side="left", padx=4)
        self.course_cb = ttk.Combobox(top, state="readonly", width=40)
        self.course_cb.pack(side="left")
        self.course_cb.bind("<<ComboboxSelected>>", lambda e: self.load())
        self.tree = make_table(self, [("no", "Numara", 90), ("name", "Ad Soyad", 170),
                                      ("mid", "Vize", 60), ("fin", "Final", 60),
                                      ("asg", "Ödev", 60), ("avg", "Ortalama", 80),
                                      ("let", "Harf", 50), ("st", "Durum", 110)])
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        form = ttk.Frame(self)
        form.pack(fill="x", pady=6)
        self.mid, self.fin, self.asg = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for i, (label, var) in enumerate((("Vize", self.mid), ("Final", self.fin),
                                          ("Ödev", self.asg))):
            ttk.Label(form, text=label).grid(row=0, column=i * 2, padx=2)
            ttk.Entry(form, textvariable=var, width=8).grid(row=0, column=i * 2 + 1)
        ttk.Button(form, text="Kaydet", command=self.save).grid(row=0, column=6, padx=8)

    def refresh(self):
        self.course_map = {f"{c.code} - {c.name}": c
                           for c in self.app.courses.list_all()}
        self.course_cb["values"] = list(self.course_map)
        self.load()

    def load(self):
        self.tree.delete(*self.tree.get_children())
        c = self.course_map.get(self.course_cb.get())
        if not c:
            return
        for eid, _term, s in self.app.enrollments.list_by_course(c.id):
            r = self.app.grades.evaluate(eid, c)
            self.tree.insert("", "end", iid=str(eid), values=(
                s.student_no, s.full_name(), fmt(r["midterm"]), fmt(r["final"]),
                fmt(r["assignment"]), fmt(r["average"]), r["letter"] or "-",
                r["status"]))

    def on_select(self, _e):
        sel = self.tree.selection()
        if sel:
            v = self.tree.item(sel[0])["values"]
            self.mid.set(v[2])
            self.fin.set(v[3])
            self.asg.set(v[4])

    def save(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showinfo("Bilgi", "Listeden bir öğrenci seçin.")
        eid = int(sel[0])

        def action():
            self.app.grades.enter_grade(eid, parse_score(self.mid.get()),
                                        parse_score(self.fin.get()),
                                        parse_score(self.asg.get()))
        if self.app.run_action(action):
            self.load()


class ReportTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.course_map, self.student_map = {}, {}
        box = ttk.LabelFrame(self, text="Öğrenci transkripti (PDF)")
        box.pack(fill="x", padx=8, pady=8)
        self.student_cb = ttk.Combobox(box, state="readonly", width=45)
        self.student_cb.pack(side="left", padx=6, pady=6)
        ttk.Button(box, text="PDF Al", command=self.pdf).pack(side="left")
        box2 = ttk.LabelFrame(self, text="Ders not listesi (CSV)")
        box2.pack(fill="x", padx=8, pady=8)
        self.course_cb = ttk.Combobox(box2, state="readonly", width=45)
        self.course_cb.pack(side="left", padx=6, pady=6)
        ttk.Button(box2, text="CSV Al", command=self.csv).pack(side="left")

    def refresh(self):
        self.student_map = {f"{s.student_no} {s.full_name()}": s
                            for s in self.app.students.list_all()}
        self.student_cb["values"] = list(self.student_map)
        self.course_map = {f"{c.code} - {c.name}": c
                           for c in self.app.courses.list_all()}
        self.course_cb["values"] = list(self.course_map)

    def pdf(self):
        s = self.student_map.get(self.student_cb.get())
        if not s:
            return messagebox.showinfo("Bilgi", "Öğrenci seçin.")
        path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                            initialfile=f"transkript_{s.student_no}.pdf")
        if path and self.app.run_action(lambda: self.app.exporter.export_transcript_pdf(s.id, path)):
            messagebox.showinfo("Tamam", f"PDF oluşturuldu:\n{path}")

    def csv(self):
        c = self.course_map.get(self.course_cb.get())
        if not c:
            return messagebox.showinfo("Bilgi", "Ders seçin.")
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            initialfile=f"notlar_{c.code}.csv")
        if path and self.app.run_action(lambda: self.app.exporter.export_course_csv(c.id, path)):
            messagebox.showinfo("Tamam", f"CSV oluşturuldu:\n{path}")
