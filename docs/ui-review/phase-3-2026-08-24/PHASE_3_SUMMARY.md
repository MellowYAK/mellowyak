# סיכום Phase 3 — MellowYak

תאריך: 2026-08-24  
ענף עבודה: `product/reverse-impact-context-foundation`  
בסיס מדויק: `38a9058990f0e4eff4e53d85019775cdde8f7931`  
מיגרציה: `0003_reverse_impact_context`

## מה הושלם

Phase 3 מוסיף שכבת מודיעין מקומית ודטרמיניסטית מעל תשתית הפרויקט ו‑Git של Phase 2:

1. זיהוי יציב של שינוי נוכחי — commit מול commit או HEAD יחד עם fingerprint של worktree לא שמור.
2. Reverse Impact מוגבל שמתחיל רק מקבצים שהשתנו ועובר בקשרים סטטיים ידועים.
3. דירוג נפרד לקשרים מדויקים, קשרי parser וקשרים heuristic.
4. נתיבי הסבר לכל תוצאה חשובה, כולל provenance ועומק.
5. עצירה כנה בגבולות `UNKNOWN` ו‑`STALE`, ללא הצגת blast radius מלא שלא הוכח.
6. Context Receipt דטרמיניסטי ומוגבל עם אפס bytes של קוד מקור ואפס העלאת מקור.
7. Behavior Candidates שמקורם בבדיקות קשורות, אך מסומנים במפורש כלא מוגנים ולא מאומתים.
8. API מקומי, מודלים, SQLite, OpenAPI וממשק React לכל היכולות האלו.
9. תיקון startup של macOS: המנוע עולה אסינכרונית והחלון אינו נחסם או קורס אחרי timeout ישן.
10. מסך startup אמיתי וקומפקטי: שמונת פריימי MellowYak נטענים מראש והשלבים נגזרים מ־health, מסד/אחסון, readiness/יכולות, איתור פרויקטים ובדיקות סופיות — ללא Ready מוקדם.

## מסד נתונים ו‑API

המיגרציה `0003_reverse_impact_context` מוסיפה ישויות עבור Changes, ניתוחי impact, inputs/results/paths, Context Receipts/items ו‑Behavior Candidates/links. מסלולי שדרוג נבדקו ממסד ריק, Phase 1 ו‑Phase 2 תוך שמירת פרויקט קיים.

החוזה נמצא ב‑`packages/contracts/openapi.json`; ה‑API והנתונים נשארים project-scoped ודורשים token מקומי לכל הפעלה.

## מה הועבר מ‑APC

לא הועתק קוד APC, מסד MariaDB, UI, tenant, משימות, credentials או deployment. APC נשאר read-only.

מה שכן הועבר הוא ידע מוצרי וארכיטקטוני שעבר ניקוי והתאמה למוצר עצמאי:

- הרעיון של context ממוקד הפך ל‑Context Receipt מקומי, מוגבל וניתן לבדיקה;
- הרעיון של project map הפך לגרף SQLite מקומי עם provenance וגבולות unknown/stale;
- רמזים להתנהגות הופרדו ל‑Behavior Candidates לא מאומתים, במקום לטעון כבר עכשיו להגנה או regression;
- עקרונות privacy, project scoping ו‑explicit authorization נשמרו, בלי סמנטיקת installation-wide של APC;
- הוסר כל coupling ל‑PHP, MariaDB, Docker, APC Bridge או חשבון APC.

מסמך ההחלטה המפורט נמצא ב‑`docs/migration/PHASE_3_APC_IMPACT_CONTEXT_EXTRACTION.md` וב‑ADRs 0006–0008.

## שפות ו‑RTL

הכלל המחייב מופיע בראש `README.md`: אין copy קשיח בממשק. כל label, title, message, placeholder, accessible name ותיאור mascot מגיע ממפתח תרגום. אנגלית היא קטלוג הבסיס; עברית מלאה ומוצגת ב‑RTL; נתיבי קוד ו‑JSON נשארים LTR. הבדיקה `scripts/check_ui_translation_keys.py` נאכפת גם ב‑CI.

## מותג ו‑mascot

- גיליון המקור השקוף נשמר ללא שינוי ונחתך אוטומטית ל‑16 תנוחות PNG עם padding נקי.
- manifest JSON ומדריך שימוש מגדירים meaning key, מסכים, tone, role וגדלים לכל תנוחה.
- השימוש בממשק מוגבל למסכים דלילים ומצבי עזרה, כדי לשמור על מוצר מקצועי ולא ילדותי.
- אייקון האפליקציה החדש נשמר ב‑`assets/brand/mellowyak-app-icon.png` וממנו הופקו קובצי macOS, Windows ו‑PNG של Tauri.

## התקנה ועדכונים

לפי ההנחיה המאוחרת של המשתמש נוספה תשתית updater חתומה, אף שהיא לא הייתה חלק מה‑scope המקורי של Phase 3:

- בדיקת `latest.json` ב‑GitHub Releases;
- אימות חתימה מול public key שמוטמע באפליקציה;
- פעולה מתורגמת להתקנה והפעלה מחדש;
- release workflow ל‑DMG, Windows NSIS `.exe`, Linux AppImage/DEB ו‑update metadata;
- private key נשאר מחוץ למאגר ואסור לפרסם אותו;
- ב‑macOS מקומי `python3 scripts/dev.py install-macos` בונה `.app` בלבד ומעדכן ישירות את `/Applications/MellowYak.app`, עם גיבוי בר־שחזור.

לא פורסם Release ולא בוצע push. מסלול עדכון מרוחק יישאר `IMPLEMENTED_NOT_RUNTIME_VERIFIED` עד שקיימת גרסה חתומה גבוהה יותר ב‑GitHub Releases. חתימת updater אינה מחליפה notarization של Apple או code signing של Windows.

## אימות שבוצע

- Python: 40 בדיקות עברו.
- React: 10 בדיקות עברו, כולל חסימת Ready מוקדם, כשל ו־Retry, ו־reduced motion.
- TypeScript ו‑Vite production build עברו.
- Ruff check/format עברו.
- Cargo check/fmt עברו.
- OpenAPI נוצר באופן דטרמיניסטי.
- packaged fixture עבר מול המנוע מתוך `/Applications/MellowYak.app` עם restart/reload, אפס source bytes ו‑loopback בלבד.
- האפליקציה המותקנת נשארה פעילה מעבר לחלון הקריסה הישן.
- 24 מסכי UI הופקו באנגלית ובעברית RTL, כולל startup וחלון צר; PDF הבדיקה מכיל 25 עמודים.

## מה לא קיים עדיין

Phase 3 אינו טוען ל‑Protected Behaviors, הרצת בדיקות אוטומטית, PASS/FAIL, Regression Detected, Last Known Good, Completion Gate, Repair Context, browser capture, connectors, accounts, cloud sync או blast radius מלא. אלה אינם מוסתרים מאחורי UI; הם שייכים לשלבים עתידיים.

Windows, Linux, Apple Silicon, notarization, Windows code signing ו‑GitHub Release אמיתי לא אומתו בזמן הריצה המקומית הזו. Remote CI לא רץ מפני שלא בוצע push.

## קבצי הסקירה בתיקייה זו

- `01`–`13`: מסכי אנגלית ומצבים מרכזיים.
- `14`–`21`: מסכי עברית RTL.
- `22`–`24`: startup אמיתי באנגלית, עברית RTL וחלון צר עם reduced motion.
- `00-app-icon-master.png`: master של אייקון האפליקציה.
- `00-mascot-sheet.png`: גיליון 16 תנוחות ה‑mascot.
- `00-loading-sprite-sheet.png`: גיליון שמונת פריימי ה־startup.
- `UI_REVIEW.md`: הסבר ופעולות לכל צילום.
- `UI_REVIEW.html`: מקור ה‑PDF הניתן לעריכה.
- `MellowYak-Phase-3-UI-Review.pdf`: מסמך חזותי בן 25 עמודים.
- `PHASE_3_SUMMARY.md`: מסמך זה.

כל הנתונים בצילומים הם fixture סינתטי וכללי. אין בתיקייה קוד מקור פרטי, credentials, כתובות שרת פרטיות או נתיבי משתמש אישיים.
