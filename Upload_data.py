"""
سكريبت رفع كل الـ CSV files إلى MongoDB Atlas
يُشغّل مرة واحدة فقط من الـ terminal: python Upload_data.py

ملحوظة: بيانات الاتصال بتُقرأ من .streamlit/secrets.toml بدل ما تكون
مكتوبة هنا مباشرة، عشان لا تترفع بالغلط على GitHub.
"""

import pandas as pd
import toml
from pymongo import MongoClient
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 1) قراءة الإعدادات من secrets.toml
# ─────────────────────────────────────────────────────────────
secrets_path = Path(".streamlit/secrets.toml")
if not secrets_path.exists():
    raise FileNotFoundError(
        "ملف .streamlit/secrets.toml غير موجود. "
        "تأكد إنك شغّال السكربت من روت المشروع."
    )

secrets = toml.load(secrets_path)
MONGO_URI = secrets["MONGO_URI"]
DB_NAME = secrets.get("DB_NAME", "kayfa_analytics")

# ملفات الـ CSV والـ collection name المقابل لكل منها
FILES = {
    "attendance":   "data/final_clean_attendance.csv",
    "courses":      "data/final_clean_courses.csv",
    "grades":       "data/final_clean_grades.csv",
    "groups":       "data/final_clean_groups.csv",
    "performance":  "data/final_clean_performance.csv",
    "students":     "data/final_clean_student.csv",
    "submissions":  "data/final_clean_submission.csv",
    "event":        "data/final_clean_event.csv",
    "master_students": "data/master_df.csv",
}

# ─────────────────────────────────────────────────────────────
# 2) الاتصال بـ MongoDB
# ─────────────────────────────────────────────────────────────
print("🔌 جاري الاتصال بـ MongoDB Atlas ...")
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
print(f"✅ متصل بـ database: {DB_NAME}\n")

# ─────────────────────────────────────────────────────────────
# 3) رفع كل ملف
# ─────────────────────────────────────────────────────────────
for collection_name, file_path in FILES.items():
    print(f"📂 قراءة: {file_path} ...")
    try:
        df = pd.read_csv(file_path)
        print(f"   ✅ {len(df)} صف | {len(df.columns)} عمود")

        records = df.to_dict(orient="records")

        collection = db[collection_name]

        # مسح البيانات القديمة قبل الرفع
        deleted = collection.delete_many({})
        print(f"   🗑️  تم مسح {deleted.deleted_count} سجل قديم")

        if records:
            result = collection.insert_many(records)
            print(f"   ⬆️  تم رفع {len(result.inserted_ids)} سجل إلى '{collection_name}' ✅")
        else:
            print(f"   ⚠️  الملف فاضي!")

    except FileNotFoundError:
        print(f"   ❌ الملف مش موجود: {file_path}")
    except Exception as e:
        print(f"   ❌ خطأ: {str(e)}")
    print()

# ─────────────────────────────────────────────────────────────
# 4) تأكيد سريع
# ─────────────────────────────────────────────────────────────
print("📊 إجمالي المستندات في كل collection:")
for collection_name in FILES.keys():
    count = db[collection_name].count_documents({})
    print(f"   {collection_name}: {count} سجل")

client.close()
print("\n🎉 انتهى!")