# Antigravity RTL & BiDi Fix

A lightweight utility to resolve Right-to-Left (RTL) text direction and English/Arabic mixed-text alignment issues in Google Antigravity's Agent Manager chat interface.

Also fully compatible with **Persian (Farsi)**, **Urdu**, **Pashto**, **Kurdish**, and any language using the Arabic script.

---

## Language / اللغة

- [English Documentation](#english)
- [التوثيق باللغة العربية](#arabic)

---

<a name="english"></a>
## English

### Key Features
1. **Targeted Scope**: Modifies only the Antigravity chat window (`Agent Manager`). Does not alter the separate code editor (`Antigravity IDE` / Monaco Editor).
2. **List Markers Fixed**: Numbers (`1.`, `2.`) and bullet points (`•`) properly align to the right edge for RTL languages, and stay on the left for LTR languages.
3. **Code Safety**: Preserves code blocks (`pre`, `code`) in strict Left-to-Right (`direction: ltr`) layout.
4. **Safety & Rollback**: Automatically creates an unpatched backup (`app.asar.backup`) before any file modification. Includes a 1-click restore feature.
5. **Idempotent**: Safe to run repeatedly; detects existing installations and updates automatically without duplicate code injection.

### Requirements
- Windows 10 / 11
- Python 3.8 or newer (ensure "Add python.exe to PATH" is checked during installation)

### How to Install & Apply
> **File Location**: You can extract and run this tool from **any location on your computer** (Desktop, Downloads, etc.). The script automatically detects the Antigravity installation path. The only requirement is that `antigravity_rtl_fix.py` and `Run_RTL_Fix.bat` remain together in the same folder.

1. Fully exit Antigravity (right-click the Antigravity icon in the Windows taskbar tray near the clock and click **Quit**).
2. Download or clone this repository.
3. Double-click **`Run_RTL_Fix.bat`**.
4. Choose option **`2`** to apply the fix.
5. Relaunch Antigravity.

### Rollback / Uninstall
To revert to the stock version at any time:
1. Close Antigravity completely.
2. Run **`Run_RTL_Fix.bat`**.
3. Choose option **`3`** to restore the original backup.

---

<a name="arabic"></a>
## العربية

أداة لإصلاح اتجاه النصوص العربية واللغات المكتوبة بالحرف العربي (الفارسية، الأردية، الكردية، البشتو، وغيرها) داخل واجهة المحادثة في برنامج Antigravity.

### المميزات الرئيسية
1. **نطاق محدد وآمن**: يستهدف واجهة المحادثة فقط (`Agent Manager`) دون المساس بملفات محرر الأكواد (`Antigravity IDE`).
2. **إصلاح ترقيم ونقاط القوائم**: نقل الترقيم والنقاط إلى جهة اليمين للنصوص العربية، مع إبقائها على اليسار للقوائم الإنجليزية.
3. **حماية الأكواد البرمجية**: إبقاء كتل وأسطر الكود (`pre`, `code`) من اليسار لليمين (`LTR`).
4. **نسخ احتياطي واستعادة بضغطة زر**: إنشاء نسخة احتياطية تلقائية (`app.asar.backup`) وإمكانية التراجع في أي وقت.
5. **عدم التكرار**: فحص مسبق لمنع تكرار الحقن والتحديث الذكي عند تثبيت إصدار أحدث.

### المتطلبات
- نظام تشغيل Windows 10 أو Windows 11.
- تثبيت بايثون (Python 3.8+) مع تفعيل خيار `Add python.exe to PATH`.

### خطوات التثبيت والتشغيل
> **مكان وجود الملفات**: يمكنك تشغيل الأداة من **أي مسار على جهازك** (سطح المكتب، التنزيلات، أو أي مجلد). السكريبت يبحث تلقائياً عن مسار تثبيت برنامج Antigravity في النظام. الشرط الوحيد هو أن يكون الملفان (`antigravity_rtl_fix.py` و `Run_RTL_Fix.bat`) معاً داخل نفس المجلد.

1. إغلاق برنامج Antigravity بالكامل (من شريط المهام بجانب الساعة: كليك يمين ثم **Quit**).
2. تشغيل الملف **`Run_RTL_Fix.bat`**.
3. اختيار الرقم **`2`** لتطبيق الإصلاح.
4. إعادة تشغيل Antigravity كالمعتاد.

### التراجع والاستعادة
1. إغلاق Antigravity بالكامل.
2. تشغيل **`Run_RTL_Fix.bat`**.
3. اختيار الرقم **`3`** لاسترجاع النسخة الأصلية فوراً.
