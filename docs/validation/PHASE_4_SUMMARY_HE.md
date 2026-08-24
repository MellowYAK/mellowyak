# סיכום פאזה 4 — התנהגויות מוגנות, ראיות ודפדפן מקומי

תאריך: 2026-08-24

סטטוס ב־Intel macOS: `VERIFIED_WORKING`

## מה בוצע

פאזה 4 מוסיפה ל־MellowYak זרימת עבודה מקומית מלאה להגדרת התנהגות חשובה, הקלטת השימוש בה בדפדפן מקומי, ביקורת אנושית על החומר שנאסף, ושמירת Last Known Good שמקושר במדויק לגרסת ההתנהגות ולגרסת המקור. המערכת אינה מציגה את החומר כ־PASS או FAIL ואינה טוענת שבוצעה בדיקה חדשה כאשר קיים רק קישור היסטורי.

נוספו גרסאות immutable להתנהגויות, מצבי lifecycle מפורשים, הגדרות runtime, capture עם pause/resume/stop/cancel, review של צעדים ותצפיות, screenshots שניתנים להסרה לפני קבלה, evidence store מבוסס SHA-256, deduplication, manifests דטרמיניסטיים, baseline שניתן לקבל או לבטל, audit trail, וקישורים מדויקים בין קובץ שהשתנה להתנהגות מוכרת.

## מה הועבר מ־APC

APC נשאר לקריאה בלבד ולא שונה. לא הועתקו קוד PHP, חשבונות, tenants, cookies, סשנים, מפתחות, נתונים, MariaDB, Bridge או הנחות שרת. נלקחו ממנו רק רעיונות שימושיים:

- lifecycle מפורש של browser runtime וחשיבות של ניקוי תהליכים;
- deny-by-default ליעדי גלישה;
- ראיות מקומיות מוגבלות בגודל ובזמן;
- הפרדה בין עובדות מקור לעובדות runtime;
- זהות תוכן והיסטוריה immutable;
- lineage, ביטול Last Known Good וזהות source revision.

הרעיונות נכתבו מחדש ב־Python/React לפי חוזי MellowYak. גבולות APC הרחבים של source/context והרשאות כלל־התקנתיות סומנו `DO_NOT_USE`.

## איך זה עובד עכשיו

המשתמש יוצר Draft של Protected Behavior, מגדיר כתובת loopback עם port מפורש, מפעיל capture בדפדפן מקומי, מבצע פעולות ב־PulsePlan או בפרויקט המקומי, עוצר ומגיע למסך review. רק אחרי בחירה מודעת של צעדים/תצפיות ו־accept נוצר bundle ונקבע baseline. כל artifact נשמר מקומית, נבדק ב־SHA-256, ולא ניתן למחוק evidence שמקושר ל־baseline מקובל.

במסך Changes מוצגים רק קישורי FILE מדויקים להתנהגויות מוכרות. הקישור מוצג כהקשר היסטורי ולא כהוכחת תקינות חדשה. קביעת PASS/FAIL, regression detection ו־Completion Gate נשארו לפאזה 5.

## שפה ו־UI

כל טקסט מוצר עובר דרך מפתחות תרגום. אנגלית היא שפת הבסיס; עברית קיימת במלואה עם RTL. נוספו מסכי Protected Behaviors, Runtime, Capture Review, Evidence ו־Last Known Good. האייקון שסופק הוכן כ־PNG ראשי ונוצרו ממנו ICNS ל־macOS ו־ICO ל־Windows.

## בדיקות ואריזה

- 68 בדיקות Python עברו.
- 12 בדיקות React עברו.
- סך הכול 80 בדיקות עברו.
- בדיקת translation keys, TypeScript/Vite, Ruff, Cargo ו־OpenAPI דטרמיניסטי עברו.
- האפליקציה ו־DMG נבנו מחדש, והאפליקציה הסופית הותקנה ב־`/Applications/MellowYak.app`.
- ולידציית package הפעילה את המנוע והדפדפן מתוך החבילה, שמרה ארבע ראיות, קיבלה baseline רק לאחר review, אתחלה מחדש, טענה את הנתונים שוב ולא השאירה תהליכים יתומים.

## מה עדיין לא נטען

בדיקת החבילה בוצעה על Intel macOS. Windows, Linux ו־Apple Silicon הם `UNKNOWN` עד הרצה אמיתית. דפדפן visible הוא ברירת המחדל בקוד, אך האימות האוטומטי של החבילה רץ headless ולכן session ידני visible הוא `IMPLEMENTED_NOT_RUNTIME_VERIFIED`. Trace/video אינם נשמרים כרגע (`PARTIAL`). לא בוצעו signing, notarization, push או release.

## מסקנה

פאזה 4 הושלמה כבסיס מקומי, מאובטח וביקורת־תחילה להתנהגויות מוגנות ולראיות דפדפן. היא מוכנה להעברת היד לפאזה 5 בלי לטעון טענות בדיקה שאינן קיימות.
