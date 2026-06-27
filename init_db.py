import sqlite3
import os

# احذف الداتابيز القديمة لو موجودة
if os.path.exists('properties.db'):
    os.remove('properties.db')
    print("تم حذف الداتابيز القديمة")

conn = sqlite3.connect('properties.db')
c = conn.cursor()

# جدول العقارات الرئيسي
c.execute('''
    CREATE TABLE properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        price INTEGER NOT NULL,
        listing_type TEXT NOT NULL,
        price_negotiable INTEGER DEFAULT 0,
        location TEXT NOT NULL,
        area INTEGER NOT NULL,
        bedrooms INTEGER DEFAULT 0,
        bathrooms INTEGER DEFAULT 0,
        property_type TEXT NOT NULL,
        description TEXT,
        features TEXT,
        phone TEXT DEFAULT '01120026602',
        map_link TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# جدول الصور
c.execute('''
    CREATE TABLE property_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        image_path TEXT NOT NULL,
        FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE CASCADE
    )
''')

print("تم إنشاء الجداول بنجاح")
conn.commit()
conn.close()
print("الداتابيز جاهزة!")