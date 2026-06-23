import tkinter as tk
from tkinter import ttk, messagebox, StringVar
import psycopg2


DB_CONFIG = {
    'dbname': 'my_pharmacy',
    'user': 'myusers',
    'password': 'myusers123',
    'host': 'localhost',
    'port': '5432'
}
def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding('UTF8')
    return conn


def load_medicines(search_text="", show_only_in_stock=False):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            SELECT drug_id, drug_name, price, stock_quantity 
            FROM drugs 
            WHERE is_active = TRUE
        """

        params = []

        if search_text:
            query += " AND drug_name ILIKE %s"
            params.append(f"%{search_text}%")

        if show_only_in_stock:
            query += " AND stock_quantity > 0"

        query += " ORDER BY drug_name"
        cur.execute(query, params)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except Exception as e:
        messagebox.showerror("Ошибка БД", f"Не удалось загрузить данные:\n{e}")
        return []


def add_medicine_to_db(name, price, stock):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO drugs (drug_name, price, stock_quantity, manufacturer_id, form_id, prescription_id, is_active)
            VALUES (%s, %s, %s, 1, 1, 2, TRUE)
        """, (name, price, stock))
        conn.commit()
        cur.close()
        conn.close()
        return True, "Лекарство успешно добавлено!"
    except Exception as e:
        return False, str(e)


def update_medicine(drug_id, price, stock):
    """Обновляет цену и количество лекарства"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE drugs 
            SET price = %s, stock_quantity = %s 
            WHERE drug_id = %s
        """, (price, stock, drug_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        return False


def delete_medicine_from_db(drug_id):
    """Мягкое удаление (просто скрываем)"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE drugs SET is_active = FALSE WHERE drug_id = %s", (drug_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        return False


def get_contraindications(drug_id):
    """Получает список противопоказаний для лекарства"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.contraindication_name, c.description
            FROM contraindications c
            JOIN drug_contraindications dc ON c.contraindication_id = dc.contraindication_id
            WHERE dc.drug_id = %s
        """, (drug_id,))
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except Exception as e:
        return []


def get_statistics():
    """Получает статистику по лекарствам"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                COUNT(*) as total_count,
                SUM(stock_quantity) as total_stock,
                SUM(price * stock_quantity) as total_value
            FROM drugs 
            WHERE is_active = TRUE
        """)
        data = cur.fetchone()
        cur.close()
        conn.close()
        return data
    except Exception as e:
        return (0, 0, 0)


# ========== ГРАФИЧЕСКИЙ ИНТЕРФЕЙС ==========

class PharmacyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Аптека — Система управления лекарствами")
        self.root.geometry("950x700")
        self.root.resizable(True, True)

        # Переменные для фильтров
        self.search_var = StringVar()
        self.show_in_stock_var = tk.BooleanVar(value=False)

        # Создаем интерфейс
        self.create_widgets()
        self.refresh_table()
        self.update_statistics()

    def create_widgets(self):
        self.frame_stats = tk.LabelFrame(self.root, text="📊 Статистика аптеки", font=("Arial", 11, "bold"))
        self.frame_stats.pack(fill="x", padx=10, pady=5)

        self.lbl_total_medicines = tk.Label(self.frame_stats, text="Всего лекарств: 0", font=("Arial", 10))
        self.lbl_total_medicines.pack(side="left", padx=15, pady=5)

        self.lbl_total_stock = tk.Label(self.frame_stats, text="Всего единиц: 0", font=("Arial", 10))
        self.lbl_total_stock.pack(side="left", padx=15, pady=5)

        self.lbl_total_value = tk.Label(self.frame_stats, text="Общая стоимость: 0 руб.", font=("Arial", 10))
        self.lbl_total_value.pack(side="left", padx=15, pady=5)

        self.frame_search = tk.LabelFrame(self.root, text="🔍 Поиск и фильтры", font=("Arial", 11, "bold"))
        self.frame_search.pack(fill="x", padx=10, pady=5)

        tk.Label(self.frame_search, text="Название:", font=("Arial", 10)).pack(side="left", padx=5)
        self.entry_search = tk.Entry(self.frame_search, textvariable=self.search_var, width=30, font=("Arial", 10))
        self.entry_search.pack(side="left", padx=5)

        self.btn_search = tk.Button(self.frame_search, text="🔍 Искать", command=self.search_medicines,
                                    bg="#2196F3", fg="white", font=("Arial", 9, "bold"))
        self.btn_search.pack(side="left", padx=5)

        self.btn_clear = tk.Button(self.frame_search, text="❌ Сбросить", command=self.clear_search,
                                   bg="#FF9800", fg="white", font=("Arial", 9, "bold"))
        self.btn_clear.pack(side="left", padx=5)

        self.chk_in_stock = tk.Checkbutton(self.frame_search, text="Только в наличии",
                                           variable=self.show_in_stock_var,
                                           command=self.search_medicines)
        self.chk_in_stock.pack(side="left", padx=15)

        # ===== ФРЕЙМ ДЛЯ ДОБАВЛЕНИЯ/РЕДАКТИРОВАНИЯ =====
        self.frame_add = tk.LabelFrame(self.root, text="➕ Добавить новое лекарство", font=("Arial", 11, "bold"))
        self.frame_add.pack(fill="x", padx=10, pady=5)

        # Поля ввода
        tk.Label(self.frame_add, text="Название:", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_name = tk.Entry(self.frame_add, width=40, font=("Arial", 10))
        self.entry_name.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self.frame_add, text="Цена (руб.):", font=("Arial", 10)).grid(row=0, column=2, padx=5, pady=5,
                                                                               sticky="w")
        self.entry_price = tk.Entry(self.frame_add, width=12, font=("Arial", 10))
        self.entry_price.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(self.frame_add, text="Количество:", font=("Arial", 10)).grid(row=0, column=4, padx=5, pady=5,
                                                                              sticky="w")
        self.entry_stock = tk.Entry(self.frame_add, width=10, font=("Arial", 10))
        self.entry_stock.grid(row=0, column=5, padx=5, pady=5)

        self.btn_add = tk.Button(self.frame_add, text="Добавить", command=self.add_medicine,
                                 bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), padx=15)
        self.btn_add.grid(row=0, column=6, padx=10, pady=5)

        # ===== ТАБЛИЦА С ЛЕКАРСТВАМИ =====
        self.frame_table = tk.LabelFrame(self.root, text="📋 Список лекарств", font=("Arial", 11, "bold"))
        self.frame_table.pack(fill="both", expand=True, padx=10, pady=5)

        # Создаем таблицу
        columns = ("id", "name", "price", "stock")
        self.tree = ttk.Treeview(self.frame_table, columns=columns, show="headings", height=15)

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Название")
        self.tree.heading("price", text="Цена (руб)")
        self.tree.heading("stock", text="Кол-во (шт)")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("name", width=500)
        self.tree.column("price", width=100, anchor="center")
        self.tree.column("stock", width=80, anchor="center")

        # Скроллбар
        scrollbar = ttk.Scrollbar(self.frame_table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Привязываем событие выбора строки
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # ===== НИЖНЯЯ ПАНЕЛЬ КНОПОК =====
        self.frame_buttons = tk.Frame(self.root)
        self.frame_buttons.pack(fill="x", padx=10, pady=5)

        self.btn_refresh = tk.Button(self.frame_buttons, text="🔄 Обновить", command=self.refresh_table,
                                     bg="#2196F3", fg="white", font=("Arial", 10, "bold"), padx=10)
        self.btn_refresh.pack(side="left", padx=5)

        self.btn_edit = tk.Button(self.frame_buttons, text="✏️ Редактировать", command=self.edit_medicine,
                                  bg="#FF9800", fg="white", font=("Arial", 10, "bold"), padx=10)
        self.btn_edit.pack(side="left", padx=5)

        self.btn_contraindications = tk.Button(self.frame_buttons, text="⚠️ Противопоказания",
                                               command=self.show_contraindications,
                                               bg="#9C27B0", fg="white", font=("Arial", 10, "bold"), padx=10)
        self.btn_contraindications.pack(side="left", padx=5)

        self.btn_delete = tk.Button(self.frame_buttons, text="🗑️ Удалить", command=self.delete_medicine,
                                    bg="#f44336", fg="white", font=("Arial", 10, "bold"), padx=10)
        self.btn_delete.pack(side="left", padx=5)

        # Информационная метка
        self.lbl_status = tk.Label(self.frame_buttons, text="✅ Готово", fg="green", font=("Arial", 9))
        self.lbl_status.pack(side="right", padx=10)

    def refresh_table(self):
        self.search_medicines()

    def search_medicines(self):
        search_text = self.search_var.get()
        show_in_stock = self.show_in_stock_var.get()

        medicines = load_medicines(search_text, show_in_stock)

        for row in self.tree.get_children():
            self.tree.delete(row)

        for med in medicines:
            self.tree.insert("", tk.END, values=med, iid=med[0])

        self.update_statistics()
        self.lbl_status.config(text=f"✅ Найдено {len(medicines)} лекарств", fg="green")

    def clear_search(self):
        self.search_var.set("")
        self.show_in_stock_var.set(False)
        self.search_medicines()

    def update_statistics(self):
        total, stock, value = get_statistics()
        self.lbl_total_medicines.config(text=f"Всего лекарств: {total}")
        self.lbl_total_stock.config(text=f"Всего единиц: {stock}")
        self.lbl_total_value.config(text=f"Общая стоимость: {value:.2f} руб.")

    def add_medicine(self):
        name = self.entry_name.get().strip()
        price_str = self.entry_price.get().strip()
        stock_str = self.entry_stock.get().strip()

        if not name:
            messagebox.showerror("Ошибка", "Введите название лекарства!")
            return

        try:
            price = float(price_str) if price_str else 0
            stock = int(stock_str) if stock_str else 0
        except ValueError:
            messagebox.showerror("Ошибка", "Цена должна быть числом, количество - целым числом!")
            return

        success, msg = add_medicine_to_db(name, price, stock)

        if success:
            messagebox.showinfo("Успех", msg)
            self.entry_name.delete(0, tk.END)
            self.entry_price.delete(0, tk.END)
            self.entry_stock.delete(0, tk.END)
            self.search_medicines()
            self.lbl_status.config(text="✅ Лекарство добавлено", fg="green")
        else:
            messagebox.showerror("Ошибка", msg)
            self.lbl_status.config(text="❌ Ошибка добавления", fg="red")

    def edit_medicine(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите лекарство для редактирования!")
            return

        drug_id = int(selected[0])
        current_values = self.tree.item(selected[0], "values")

        # Диалог редактирования
        dialog = tk.Toplevel(self.root)
        dialog.title("Редактирование лекарства")
        dialog.geometry("400x250")
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(dialog, text="Название:", font=("Arial", 11)).pack(pady=5)
        lbl_name = tk.Label(dialog, text=current_values[1], font=("Arial", 11, "bold"), fg="blue")
        lbl_name.pack(pady=5)

        tk.Label(dialog, text="Цена (руб.):", font=("Arial", 11)).pack(pady=5)
        entry_price = tk.Entry(dialog, width=15, font=("Arial", 11))
        entry_price.insert(0, current_values[2])
        entry_price.pack(pady=5)

        tk.Label(dialog, text="Количество (шт.):", font=("Arial", 11)).pack(pady=5)
        entry_stock = tk.Entry(dialog, width=15, font=("Arial", 11))
        entry_stock.insert(0, current_values[3])
        entry_stock.pack(pady=5)

        def save_changes():
            try:
                new_price = float(entry_price.get())
                new_stock = int(entry_stock.get())
            except ValueError:
                messagebox.showerror("Ошибка", "Цена должна быть числом, количество - целым числом!")
                return

            if update_medicine(drug_id, new_price, new_stock):
                messagebox.showinfo("Успех", "Изменения сохранены!")
                dialog.destroy()
                self.search_medicines()
                self.lbl_status.config(text="✅ Лекарство обновлено", fg="green")
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить изменения!")

        btn_save = tk.Button(dialog, text="Сохранить", command=save_changes,
                             bg="#4CAF50", fg="white", font=("Arial", 11, "bold"), padx=20)
        btn_save.pack(pady=20)

    def show_contraindications(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите лекарство для просмотра противопоказаний!")
            return

        drug_id = int(selected[0])
        drug_name = self.tree.item(selected[0], "values")[1]

        contraindications = get_contraindications(drug_id)

        # Создаем окно с противопоказаниями
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Противопоказания — {drug_name}")
        dialog.geometry("500x400")
        dialog.grab_set()

        if not contraindications:
            tk.Label(dialog, text="⚠️ Нет данных о противопоказаниях",
                     font=("Arial", 12), fg="orange").pack(pady=50)
        else:
            text_widget = tk.Text(dialog, wrap="word", font=("Arial", 10))
            text_widget.pack(fill="both", expand=True, padx=10, pady=10)

            for c in contraindications:
                text_widget.insert(tk.END, f"• {c[0]}\n")
                text_widget.insert(tk.END, f"  {c[1]}\n\n")

            text_widget.config(state="disabled")

        btn_close = tk.Button(dialog, text="Закрыть", command=dialog.destroy,
                              bg="#2196F3", fg="white", font=("Arial", 10, "bold"), padx=15)
        btn_close.pack(pady=10)

    def delete_medicine(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите лекарство для удаления!")
            return

        drug_id = int(selected[0])
        drug_name = self.tree.item(selected[0], "values")[1]

        if messagebox.askyesno("Подтверждение", f"Удалить лекарство '{drug_name}'?\n(оно будет скрыто из списка)"):
            if delete_medicine_from_db(drug_id):
                messagebox.showinfo("Успех", "Лекарство удалено!")
                self.search_medicines()
                self.lbl_status.config(text="✅ Лекарство удалено", fg="green")
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить лекарство!")

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            self.lbl_status.config(text="ℹ️ Выберите действие: редактировать, просмотреть противопоказания или удалить",
                                   fg="blue")
        else:
            self.lbl_status.config(text="✅ Готово", fg="green")


# ========== ЗАПУСК ПРИЛОЖЕНИЯ ==========
if __name__ == "__main__":
    root = tk.Tk()
    app = PharmacyApp(root)
    root.mainloop()