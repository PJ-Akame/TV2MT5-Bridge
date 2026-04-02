//+------------------------------------------------------------------+
//|                                          MarketHoursDisplay.mq5 |
//|  東京・ロンドン・NY 市場帯＋任意セッション・危険帯・注意帯表示     |
//|  時刻: 取引サーバー または 日本時間(JST)。JST時は英米夏冬を暦日で切替   |
//+------------------------------------------------------------------+
#property copyright "SMCSE"
#property link      ""
#property version   "2.20"
#property indicator_chart_window
#property indicator_plots 0
#property indicator_buffers 0

#define OBJ_PREFIX "MHD_"
#define SEC_DAY    86400

enum ENUM_MHD_CLOCK
  {
   MHD_CLOCK_SERVER = 0,  // 取引サーバーの HH:MM（従来）
   MHD_CLOCK_JST    = 1   // 日本標準時(JST)。自動でサーバー時刻に換算
  };

//--- 共通
input group "共通"
input ENUM_MHD_CLOCK    InpClock       = MHD_CLOCK_JST; // 市場帯の時刻の基準
input int               InpDaysBack    = 14;       // 過去に描画する日数（本日含む）
input int               InpDaysForward = 2;        // 未来に描画する日数
input int               InpRefreshSec = 30;      // 再描画間隔（秒）
input bool              InpShowLegend  = true;     // 凡例ラベル表示
input int               InpCorner      = 0;       // 凡例: 0=左上 1=右上 2=左下 3=右下
input int               InpLegendX     = 8;
input int               InpLegendY     = 18;
input int               InpLegendSize  = 8;
input color             InpLegendColor = C'148,150,154'; // 落ち着いたグレー

//--- 下部国名（開始時刻＝ラベル左端、表示域内の下端付近価格に OBJ_TEXT）
input group "下部国名ラベル"
input bool              InpShowCountryFooter = true;
input double            InpFooterLiftPct   = 2.5;   // 表示中の価格幅に対する％：下端からこの分だけ上に国名下端を配置
input int               InpFooterFontSize  = 9;
input color             InpFooterColor    = C'148,150,154';
input string            Tokyo_CountryLabel = "日本";
input string            London_CountryLabel = "英国";
input string            NY_CountryLabel    = "米国";
input string            S4_CountryLabel   = "";        // 空=非表示（例: オーストラリア）

//--- 透明度: 0=不透明(濃い) … 100=ほぼ透明（見えない）※既定80＝だいたい80%透明

//--- JST 入力（InpClock=JST のとき。ロンドン/NY の夏冬は BST・米DST の暦日で切替）
input group "市場時間(JST) ※InpClock=JST"
input int               Tokyo_JST_SH = 9, Tokyo_JST_SM = 0, Tokyo_JST_EH = 10, Tokyo_JST_EM = 0;
input int               London_JST_Su_SH = 16, London_JST_Su_SM = 0, London_JST_Su_EH = 17, London_JST_Su_EM = 0; // 英国夏(BST期)
input int               London_JST_Wi_SH = 17, London_JST_Wi_SM = 0, London_JST_Wi_EH = 18, London_JST_Wi_EM = 0; // 英国冬
input int               NY_JST_Su_SH = 22, NY_JST_Su_SM = 30, NY_JST_Su_EH = 23, NY_JST_Su_EM = 30;           // 米夏(EDT期)
input int               NY_JST_Wi_SH = 23, NY_JST_Wi_SM = 30, NY_JST_Wi_EH = 0, NY_JST_Wi_EM = 30;            // 米冬（終了は翌日0:30 JST）

//--- 東京市場
input group "東京市場"
input bool              Tokyo_Enable   = true;
input string            Tokyo_Name     = "Tokyo";
input int               Tokyo_SH = 0, Tokyo_SM = 0, Tokyo_EH = 9, Tokyo_EM = 0;  // InpClock=SERVER 用 HH:MM
input color             Tokyo_Color    = C'72,88,108';   // スレートブルー系
input int               Tokyo_Transp   = 80;
input bool              Tokyo_DangerEn = true;        // ON: 市場開始から1時間を危険帯
input color             Tokyo_DangerCol = C'110,92,98'; // ダスティローズ
input int               Tokyo_DangerTransp = 80;

//--- ロンドン市場（サマータイム: 英国BST の暦日で市場開始・終了に +1h／危険は開始から1h）
input group "ロンドン市場"
input bool              London_Enable   = true;
input string            London_Name     = "London";
input int               London_SH = 8, London_SM = 0, London_EH = 17, London_EM = 0; // SERVER 用
input bool              London_DST      = true;   // SERVER のみ: BST 暦日で +1時間
input color             London_Color    = C'82,98,86';   // ミューテッドセージ
input int               London_Transp   = 80;
input bool              London_DangerEn = true;       // ON: 市場開始から1時間（ST反映後の開始）
input color             London_DangerCol = C'108,94,82'; // ダスティアンバー
input int               London_DangerTransp = 80;

//--- NY市場（サマータイム: 米東部の暦日で市場開始・終了に +1h／危険は開始から1h）
input group "NY市場"
input bool              NY_Enable       = true;
input string            NY_Name         = "NewYork";
input int               NY_SH = 13, NY_SM = 0, NY_EH = 22, NY_EM = 0; // SERVER 用
input bool              NY_DST          = true;   // SERVER のみ: 米DST 暦日で +1時間
input color             NY_Color        = C'96,84,110';  // ダスティモーブ
input int               NY_Transp       = 80;
input bool              NY_DangerEn     = true;       // ON: 市場開始から1時間（ST反映後の開始）
input color             NY_DangerCol    = C'112,88,96';
input int               NY_DangerTransp = 80;

//--- Session 4（常に取引サーバー時刻。JST モードでもここだけサーバー基準）
input group "Session 4"
input bool              S4_Enable     = false;
input string            S4_Name       = "Sydney";
input int               S4_SH = 22, S4_SM = 0, S4_EH = 7, S4_EM = 0;  // 終了<開始で翌日まで
input color             S4_Color      = C'92,94,104';   // クールグレー
input int               S4_Transp     = 80;
input bool              S4_DangerEn   = false;
input int               S4_DSH = 22, S4_DSM = 0, S4_DEH = 23, S4_DEM = 0;
input color             S4_DangerCol  = C'100,82,78';
input int               S4_DangerTransp = 80;

//--- 単独注意帯（取引サーバー時刻）
input group "単独注意帯（セッション外）"
input bool              X1_Enable     = true;
input string            X1_Name       = "Roll/薄商い帯";
input int               X1_SH = 21, X1_SM = 0, X1_EH = 23, X1_EM = 0;
input color             X1_Color      = C'96,88,72';   // ウォームトープ
input int               X1_Transp     = 80;
input bool              X2_Enable     = false;
input string            X2_Name       = "Custom X2";
input int               X2_SH = 0, X2_SM = 0, X2_EH = 1, X2_EM = 0;
input color             X2_Color      = C'78,70,84';   // ディーププラムグレー
input int               X2_Transp     = 80;

//+------------------------------------------------------------------+
//| ARGB: transp 0=不透明 … 100=透明                                 |
//+------------------------------------------------------------------+
uint ColorToArgb(const color clr, const int transp)
  {
   int t = MathMax(0, MathMin(100, transp));
   uchar a = (uchar)(255 * (100 - t) / 100);
   return ColorToARGB(clr, a);
  }

//+------------------------------------------------------------------+
datetime DayStartServer(const datetime t)
  {
   MqlDateTime m;
   TimeToStruct(t, m);
   m.hour = 0;
   m.min  = 0;
   m.sec  = 0;
   return StructToTime(m);
  }

//+------------------------------------------------------------------+
string DayTag(const datetime d0)
  {
   MqlDateTime m;
   TimeToStruct(d0, m);
   return StringFormat("%04d%02d%02d", m.year, m.mon, m.day);
  }

//+------------------------------------------------------------------+
void AddHoursHm(int &h, int &mi, const int dh)
  {
   int x = h * 60 + mi + dh * 60;
   x %= (24 * 60);
   if(x < 0)
      x += (24 * 60);
   h = x / 60;
   mi = x % 60;
  }

//+------------------------------------------------------------------+
// 危険帯: 市場開始(sh:sm)からちょうど1時間（HH:MM、24h 繰り上げ）
void DangerHmFirstHour(const int sh, const int sm, int &dsh, int &dsm, int &deh, int &dem)
  {
   dsh = sh;
   dsm = sm;
   deh = sh;
   dem = sm;
   AddHoursHm(deh, dem, 1);
  }

//+------------------------------------------------------------------+
int NthSundayOfMonth(const int year, const int month, const int n)
  {
   if(n < 1)
      return -1;
   int cnt = 0;
   for(int d = 1; d <= 31; d++)
     {
      MqlDateTime t;
      t.year = year;
      t.mon = month;
      t.day = d;
      t.hour = 12;
      t.min = 0;
      t.sec = 0;
      datetime ts = StructToTime(t);
      if(ts == 0)
         continue;
      MqlDateTime u;
      TimeToStruct(ts, u);
      if(u.day_of_week == 0)
        {
         cnt++;
         if(cnt == n)
            return d;
        }
     }
   return -1;
  }

//+------------------------------------------------------------------+
int LastSundayOfMonth(const int year, const int month)
  {
   for(int d = 31; d >= 1; d--)
     {
      MqlDateTime t;
      t.year = year;
      t.mon = month;
      t.day = d;
      t.hour = 12;
      t.min = 0;
      t.sec = 0;
      datetime ts = StructToTime(t);
      if(ts == 0)
         continue;
      MqlDateTime u;
      TimeToStruct(ts, u);
      if(u.mon == month && u.day == d && u.day_of_week == 0)
         return d;
     }
   return -1;
  }

//+------------------------------------------------------------------+
// 英国BSTの暦日（概算）: 3月最終日曜～10月最終日曜未満（サーバー暦・描画日 d0）
bool CalendarDayUkBst(const int y, const int mon, const int day)
  {
   int lsMar = LastSundayOfMonth(y, 3);
   int lsOct = LastSundayOfMonth(y, 10);
   if(lsMar < 0 || lsOct < 0)
      return false;
   if(mon < 3 || mon > 10)
      return false;
   if(mon > 3 && mon < 10)
      return true;
   if(mon == 3)
      return (day >= lsMar);
   if(mon == 10)
      return (day < lsOct);
   return false;
  }

//+------------------------------------------------------------------+
// 米東部DSTの暦日（概算）: 3月第2日曜～11月第1日曜未満
bool CalendarDayUsEasternDst(const int y, const int mon, const int day)
  {
   int dMar = NthSundayOfMonth(y, 3, 2);
   int dNov = NthSundayOfMonth(y, 11, 1);
   if(dMar < 0 || dNov < 0)
      return false;
   if(mon < 3)
      return false;
   if(mon > 11)
      return false;
   if(mon > 3 && mon < 11)
      return true;
   if(mon == 3)
      return (day >= dMar);
   if(mon == 11)
      return (day < dNov);
   return false;
  }

//+------------------------------------------------------------------+
void MaybeShiftLondonSt(const datetime d0, const bool dstOn,
                        int &sh, int &sm, int &eh, int &em)
  {
   if(!dstOn)
      return;
   MqlDateTime dm;
   TimeToStruct(d0, dm);
   if(!CalendarDayUkBst(dm.year, dm.mon, dm.day))
      return;
   AddHoursHm(sh, sm, 1);
   AddHoursHm(eh, em, 1);
  }

//+------------------------------------------------------------------+
void MaybeShiftNySt(const datetime d0, const bool dstOn,
                    int &sh, int &sm, int &eh, int &em)
  {
   if(!dstOn)
      return;
   MqlDateTime dm;
   TimeToStruct(d0, dm);
   if(!CalendarDayUsEasternDst(dm.year, dm.mon, dm.day))
      return;
   AddHoursHm(sh, sm, 1);
   AddHoursHm(eh, em, 1);
  }

//+------------------------------------------------------------------+
void DeleteMhdObjects()
  {
   int n = ObjectsTotal(0, 0, -1);
   for(int i = n - 1; i >= 0; i--)
     {
      string nm = ObjectName(0, i, 0);
      if(nm != "" && StringFind(nm, OBJ_PREFIX) == 0)
         ObjectDelete(0, nm);
     }
  }

//+------------------------------------------------------------------+
bool CreateRect(const string name,
                const datetime t1, const datetime t2,
                const double pTop, const double pBot,
                const uint argbFill, const uint argbBorder,
                const int zorder)
  {
   if(t2 <= t1)
      return false;
   if(ObjectFind(0, name) >= 0)
      ObjectDelete(0, name);
   if(!ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, pTop, t2, pBot))
      return false;
   ObjectSetInteger(0, name, OBJPROP_COLOR, argbBorder);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, argbFill);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
   ObjectSetInteger(0, name, OBJPROP_FILL, true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_ZORDER, zorder);
   return true;
  }

//+------------------------------------------------------------------+
// 現在表示されている CHART_PRICE_MIN～MAX の範囲内で、下端付近の価格（国名アンカー用）
double VisibleChartFooterPrice()
  {
   double vMax = ChartGetDouble(0, CHART_PRICE_MAX, 0);
   double vMin = ChartGetDouble(0, CHART_PRICE_MIN, 0);
   if(vMax <= vMin)
     {
      double b = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      vMax = b * 1.002;
      vMin = b * 0.998;
     }
   double span = vMax - vMin;
   double pct = InpFooterLiftPct;
   if(pct < 0.1)
      pct = 0.1;
   if(pct > 40.0)
      pct = 40.0;
   double off = span * (pct / 100.0);
   if(off < _Point * 8)
      off = _Point * 20;
   double p = vMin + off;
   if(p >= vMax)
      p = vMin + span * 0.5;
   return p;
  }

//+------------------------------------------------------------------+
// セッション開始 t1 をラベル左端（下辺）に合わせ、priceAnchor は表示域内の価格
void DrawSessionCountryFooter(const string mktId, const string dayTag, const datetime d0,
                              const int sh, const int sm, const int eh, const int em,
                              const double priceAnchor, const string countryLabel, const color txtCol)
  {
   if(!InpShowCountryFooter || countryLabel == "")
      return;
   datetime t1, t2;
   SessionBounds(d0, sh, sm, eh, em, t1, t2);
   if(t2 <= t1)
      return;

   string nm = OBJ_PREFIX + "CF_" + mktId + "_" + dayTag;
   if(ObjectFind(0, nm) >= 0)
      ObjectDelete(0, nm);
   if(!ObjectCreate(0, nm, OBJ_TEXT, 0, t1, priceAnchor))
      return;
   ObjectSetString(0, nm, OBJPROP_TEXT, countryLabel);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, txtCol);
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, InpFooterFontSize);
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, ANCHOR_LEFT_LOWER);
   ObjectSetInteger(0, nm, OBJPROP_BACK, false);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, nm, OBJPROP_ZORDER, 50);
  }

//+------------------------------------------------------------------+
void DrawSessionCountryFooterAtTime(const string mktId, const string dayTag,
                                    const datetime t1, const double priceAnchor,
                                    const string countryLabel, const color txtCol)
  {
   if(!InpShowCountryFooter || countryLabel == "")
      return;

   string nm = OBJ_PREFIX + "CF_" + mktId + "_" + dayTag;
   if(ObjectFind(0, nm) >= 0)
      ObjectDelete(0, nm);
   if(!ObjectCreate(0, nm, OBJ_TEXT, 0, t1, priceAnchor))
      return;
   ObjectSetString(0, nm, OBJPROP_TEXT, countryLabel);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, txtCol);
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, InpFooterFontSize);
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, ANCHOR_LEFT_LOWER);
   ObjectSetInteger(0, nm, OBJPROP_BACK, false);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, nm, OBJPROP_ZORDER, 50);
  }

//+------------------------------------------------------------------+
// 1日アンカー d0（00:00 サーバー）からの時分で時刻を生成
datetime TOnDay(const datetime d0, const int h, const int mi)
  {
   return d0 + (datetime)(h * 3600 + mi * 60);
  }

//+------------------------------------------------------------------+
// セッション [t1,t2) 。終了<=開始なら翌日まで伸ばす
void SessionBounds(const datetime d0,
                   const int sh, const int sm, const int eh, const int em,
                   datetime &t1, datetime &tSessEnd)
  {
   t1 = TOnDay(d0, sh, sm);
   tSessEnd = TOnDay(d0, eh, em);
   if(tSessEnd <= t1)
      tSessEnd += SEC_DAY;
  }

//+------------------------------------------------------------------+
// JST は常に UTC+9。サーバー時刻との壁時計差 = 9h - (サーバー-GMT)
long JstAheadOfServerSec()
  {
   return (long)(9 * 3600 - (TimeTradeServer() - TimeGMT()));
  }

//+------------------------------------------------------------------+
// 「サーバー暦の d0 日」に JST の jh:jm が付く同一瞬間（概算・同一座標系の d0 基準）
datetime JstHmOnServerCalendarDay(const datetime d0, const int jh, const int jm)
  {
   return d0 + (datetime)(jh * 3600 + jm * 60) - (datetime)JstAheadOfServerSec();
  }

//+------------------------------------------------------------------+
void SessionBoundsFromJst(const datetime d0,
                          const int jsh, const int jsm, const int jeh, const int jem,
                          datetime &t1, datetime &t2)
  {
   t1 = JstHmOnServerCalendarDay(d0, jsh, jsm);
   t2 = JstHmOnServerCalendarDay(d0, jeh, jem);
   if(t2 <= t1)
      t2 += SEC_DAY;
  }

//+------------------------------------------------------------------+
void ClipRange(datetime &a1, datetime &a2, const datetime b1, const datetime b2)
  {
   if(a1 < b1)
      a1 = b1;
   if(a2 > b2)
      a2 = b2;
  }

//+------------------------------------------------------------------+
void DrawOneSession(const string sid, const string dayTag, const datetime d0,
                    const int sh, const int sm, const int eh, const int em,
                    const color col, const int transp,
                    const bool dEn,
                    const int dsh, const int dsm, const int deh, const int dem,
                    const color dcol, const int dtr,
                    const double pTop, const double pBot)
  {
   datetime t1, t2;
   SessionBounds(d0, sh, sm, eh, em, t1, t2);

   string nb = OBJ_PREFIX + sid + "_" + dayTag + "_b";
   uint af = ColorToArgb(col, transp);
   uint ab = ColorToArgb(col, MathMin(99, transp + 5));
   CreateRect(nb, t1, t2, pTop, pBot, af, ab, 10);

   if(!dEn)
      return;

   datetime d1 = TOnDay(d0, dsh, dsm);
   datetime d2 = TOnDay(d0, deh, dem);
   if(d2 <= d1)
      d2 += SEC_DAY;
   ClipRange(d1, d2, t1, t2);
   if(d2 <= d1)
      return;

   string nd = OBJ_PREFIX + sid + "_" + dayTag + "_d";
   uint df = ColorToArgb(dcol, dtr);
   uint db = ColorToArgb(dcol, MathMax(0, dtr - 8));
   CreateRect(nd, d1, d2, pTop, pBot, df, db, 20);
  }

//+------------------------------------------------------------------+
// 既知の絶対時刻 t1,t2 で市場帯（JST 換算後など）
void DrawOneSessionAbs(const string sid, const string dayTag,
                       const datetime t1, const datetime t2,
                       const color col, const int transp,
                       const bool dEn, const color dcol, const int dtr,
                       const double pTop, const double pBot)
  {
   if(t2 <= t1)
      return;
   string nb = OBJ_PREFIX + sid + "_" + dayTag + "_b";
   uint af = ColorToArgb(col, transp);
   uint ab = ColorToArgb(col, MathMin(99, transp + 5));
   CreateRect(nb, t1, t2, pTop, pBot, af, ab, 10);

   if(!dEn)
      return;

   datetime d1 = t1;
   datetime d2 = t1 + (datetime)3600;
   ClipRange(d1, d2, t1, t2);
   if(d2 <= d1)
      return;

   string nd = OBJ_PREFIX + sid + "_" + dayTag + "_d";
   uint df = ColorToArgb(dcol, dtr);
   uint db = ColorToArgb(dcol, MathMax(0, dtr - 8));
   CreateRect(nd, d1, d2, pTop, pBot, df, db, 20);
  }

//+------------------------------------------------------------------+
void DrawStandalone(const string xid, const string dayTag, const datetime d0,
                    const int sh, const int sm, const int eh, const int em,
                    const color col, const int transp,
                    const double pTop, const double pBot, const int z)
  {
   datetime t1, t2;
   SessionBounds(d0, sh, sm, eh, em, t1, t2);
   string n = OBJ_PREFIX + xid + "_" + dayTag + "_x";
   uint af = ColorToArgb(col, transp);
   uint ab = ColorToArgb(col, MathMin(99, transp + 5));
   CreateRect(n, t1, t2, pTop, pBot, af, ab, z);
  }

//+------------------------------------------------------------------+
void ChartPriceExtent(double &pTop, double &pBot)
  {
   pTop = ChartGetDouble(0, CHART_PRICE_MAX, 0);
   pBot = ChartGetDouble(0, CHART_PRICE_MIN, 0);
   if(pTop <= pBot)
     {
      pTop = SymbolInfoDouble(_Symbol, SYMBOL_BID) * 1.01;
      pBot = SymbolInfoDouble(_Symbol, SYMBOL_BID) * 0.99;
     }
   double pad = (pTop - pBot) * 0.02;
   if(pad < _Point * 10)
      pad = _Point * 50;
   pTop += pad;
   pBot -= pad;
  }

//+------------------------------------------------------------------+
void RedrawAllBands()
  {
   DeleteMhdObjects();

   double pTop, pBot;
   ChartPriceExtent(pTop, pBot);
   const double pFooter = VisibleChartFooterPrice();

   datetime now = TimeTradeServer();
   datetime dToday = DayStartServer(now);

   for(int k = -InpDaysForward; k <= InpDaysBack; k++)
     {
      datetime d0 = (datetime)((long)dToday + (long)k * SEC_DAY);
      string tag = DayTag(d0);

      if(InpClock == MHD_CLOCK_JST)
        {
         if(Tokyo_Enable)
           {
            datetime t1j, t2j;
            SessionBoundsFromJst(d0, Tokyo_JST_SH, Tokyo_JST_SM, Tokyo_JST_EH, Tokyo_JST_EM, t1j, t2j);
            DrawOneSessionAbs("TKY", tag, t1j, t2j, Tokyo_Color, Tokyo_Transp, Tokyo_DangerEn,
                              Tokyo_DangerCol, Tokyo_DangerTransp, pTop, pBot);
            DrawSessionCountryFooterAtTime("TKY", tag, t1j, pFooter, Tokyo_CountryLabel, InpFooterColor);
           }

         if(London_Enable)
           {
            MqlDateTime dml;
            TimeToStruct(d0, dml);
            datetime t1j, t2j;
            if(CalendarDayUkBst(dml.year, dml.mon, dml.day))
               SessionBoundsFromJst(d0, London_JST_Su_SH, London_JST_Su_SM, London_JST_Su_EH, London_JST_Su_EM, t1j, t2j);
            else
               SessionBoundsFromJst(d0, London_JST_Wi_SH, London_JST_Wi_SM, London_JST_Wi_EH, London_JST_Wi_EM, t1j, t2j);
            DrawOneSessionAbs("LON", tag, t1j, t2j, London_Color, London_Transp, London_DangerEn,
                              London_DangerCol, London_DangerTransp, pTop, pBot);
            DrawSessionCountryFooterAtTime("LON", tag, t1j, pFooter, London_CountryLabel, InpFooterColor);
           }

         if(NY_Enable)
           {
            MqlDateTime dmn;
            TimeToStruct(d0, dmn);
            datetime t1j, t2j;
            if(CalendarDayUsEasternDst(dmn.year, dmn.mon, dmn.day))
               SessionBoundsFromJst(d0, NY_JST_Su_SH, NY_JST_Su_SM, NY_JST_Su_EH, NY_JST_Su_EM, t1j, t2j);
            else
               SessionBoundsFromJst(d0, NY_JST_Wi_SH, NY_JST_Wi_SM, NY_JST_Wi_EH, NY_JST_Wi_EM, t1j, t2j);
            DrawOneSessionAbs("NYC", tag, t1j, t2j, NY_Color, NY_Transp, NY_DangerEn,
                              NY_DangerCol, NY_DangerTransp, pTop, pBot);
            DrawSessionCountryFooterAtTime("NYC", tag, t1j, pFooter, NY_CountryLabel, InpFooterColor);
           }
        }
      else
        {
         if(Tokyo_Enable)
           {
            int tsh = Tokyo_SH, tsm = Tokyo_SM, teh = Tokyo_EH, tem = Tokyo_EM;
            int tdsh = 0, tdsm = 0, tdeh = 0, tdem = 0;
            if(Tokyo_DangerEn)
               DangerHmFirstHour(tsh, tsm, tdsh, tdsm, tdeh, tdem);
            DrawOneSession("TKY", tag, d0, tsh, tsm, teh, tem, Tokyo_Color, Tokyo_Transp,
                           Tokyo_DangerEn, tdsh, tdsm, tdeh, tdem, Tokyo_DangerCol, Tokyo_DangerTransp, pTop, pBot);
            DrawSessionCountryFooter("TKY", tag, d0, tsh, tsm, teh, tem, pFooter, Tokyo_CountryLabel, InpFooterColor);
           }

         if(London_Enable)
           {
            int lsh = London_SH, lsm = London_SM, leh = London_EH, lem = London_EM;
            MaybeShiftLondonSt(d0, London_DST, lsh, lsm, leh, lem);
            int ldsh = 0, ldsm = 0, ldeh = 0, ldem = 0;
            if(London_DangerEn)
               DangerHmFirstHour(lsh, lsm, ldsh, ldsm, ldeh, ldem);
            DrawOneSession("LON", tag, d0, lsh, lsm, leh, lem, London_Color, London_Transp,
                           London_DangerEn, ldsh, ldsm, ldeh, ldem, London_DangerCol, London_DangerTransp, pTop, pBot);
            DrawSessionCountryFooter("LON", tag, d0, lsh, lsm, leh, lem, pFooter, London_CountryLabel, InpFooterColor);
           }

         if(NY_Enable)
           {
            int nsh = NY_SH, nsm = NY_SM, neh = NY_EH, nem = NY_EM;
            MaybeShiftNySt(d0, NY_DST, nsh, nsm, neh, nem);
            int ndsh = 0, ndsm = 0, ndeh = 0, ndem = 0;
            if(NY_DangerEn)
               DangerHmFirstHour(nsh, nsm, ndsh, ndsm, ndeh, ndem);
            DrawOneSession("NYC", tag, d0, nsh, nsm, neh, nem, NY_Color, NY_Transp,
                           NY_DangerEn, ndsh, ndsm, ndeh, ndem, NY_DangerCol, NY_DangerTransp, pTop, pBot);
            DrawSessionCountryFooter("NYC", tag, d0, nsh, nsm, neh, nem, pFooter, NY_CountryLabel, InpFooterColor);
           }
        }

      if(S4_Enable)
        {
         DrawOneSession("S4", tag, d0, S4_SH, S4_SM, S4_EH, S4_EM, S4_Color, S4_Transp,
                        S4_DangerEn, S4_DSH, S4_DSM, S4_DEH, S4_DEM, S4_DangerCol, S4_DangerTransp, pTop, pBot);
         DrawSessionCountryFooter("S4", tag, d0, S4_SH, S4_SM, S4_EH, S4_EM, pFooter, S4_CountryLabel, InpFooterColor);
        }

      if(X1_Enable)
         DrawStandalone("X1", tag, d0, X1_SH, X1_SM, X1_EH, X1_EM, X1_Color, X1_Transp, pTop, pBot, 30);
      if(X2_Enable)
         DrawStandalone("X2", tag, d0, X2_SH, X2_SM, X2_EH, X2_EM, X2_Color, X2_Transp, pTop, pBot, 30);
     }

   if(InpShowLegend)
      DrawLegend();
   else
     {
      if(ObjectFind(0, OBJ_PREFIX + "Legend") >= 0)
         ObjectDelete(0, OBJ_PREFIX + "Legend");
     }

   ChartRedraw(0);
  }

//+------------------------------------------------------------------+
void DrawLegend()
  {
   string name = OBJ_PREFIX + "Legend";
   string txt = "";
   if(InpClock == MHD_CLOCK_JST)
     {
      int jstH = (int)MathRound((double)JstAheadOfServerSec() / 3600.0);
      txt = "市場/注意 (入力JST→チャートはサーバー時刻)\n";
      txt += StringFormat("JSTはサーバー壁時計より約%+d時間\n", jstH);
      if(Tokyo_Enable)
         txt += StringFormat("■ %s %02d:%02d-%02d:%02d JST 危険:%s\n", Tokyo_Name,
                             Tokyo_JST_SH, Tokyo_JST_SM, Tokyo_JST_EH, Tokyo_JST_EM,
                             Tokyo_DangerEn ? "開始1h" : "OFF");
      if(London_Enable)
         txt += StringFormat("■ %s 夏%02d:%02d-%02d:%02d / 冬%02d:%02d-%02d:%02d JST 危険:%s\n", London_Name,
                             London_JST_Su_SH, London_JST_Su_SM, London_JST_Su_EH, London_JST_Su_EM,
                             London_JST_Wi_SH, London_JST_Wi_SM, London_JST_Wi_EH, London_JST_Wi_EM,
                             London_DangerEn ? "開始1h" : "OFF");
      if(NY_Enable)
         txt += StringFormat("■ %s 夏%02d:%02d-%02d:%02d / 冬%02d:%02d-%02d:%02d JST 危険:%s\n", NY_Name,
                             NY_JST_Su_SH, NY_JST_Su_SM, NY_JST_Su_EH, NY_JST_Su_EM,
                             NY_JST_Wi_SH, NY_JST_Wi_SM, NY_JST_Wi_EH, NY_JST_Wi_EM,
                             NY_DangerEn ? "開始1h" : "OFF");
      txt += "(S4/X1/X2はサーバー時刻入力)\n";
     }
   else
     {
      txt = "市場/注意ブロック (サーバー時刻)\n";
      if(Tokyo_Enable)
         txt += StringFormat("■ %s  %02d:%02d-%02d:%02d  危険:%s\n", Tokyo_Name, Tokyo_SH, Tokyo_SM, Tokyo_EH, Tokyo_EM,
                             Tokyo_DangerEn ? "開始1h" : "OFF");
      if(London_Enable)
         txt += StringFormat("■ %s  %02d:%02d-%02d:%02d  ST+1h:%s 危険:%s\n",
                             London_Name, London_SH, London_SM, London_EH, London_EM, London_DST ? "ON" : "OFF",
                             London_DangerEn ? "開始1h" : "OFF");
      if(NY_Enable)
         txt += StringFormat("■ %s  %02d:%02d-%02d:%02d  ST+1h:%s 危険:%s\n",
                             NY_Name, NY_SH, NY_SM, NY_EH, NY_EM, NY_DST ? "ON" : "OFF",
                             NY_DangerEn ? "開始1h" : "OFF");
     }
   if(S4_Enable)
      txt += StringFormat("■ %s  %02d:%02d-%02d:%02d (危険: %s)\n", S4_Name, S4_SH, S4_SM, S4_EH, S4_EM, S4_DangerEn ? "ON" : "OFF");
   if(X1_Enable)
      txt += StringFormat("▣ %s  %02d:%02d-%02d:%02d (単独)\n", X1_Name, X1_SH, X1_SM, X1_EH, X1_EM);
   if(X2_Enable)
      txt += StringFormat("▣ %s  %02d:%02d-%02d:%02d (単独)\n", X2_Name, X2_SH, X2_SM, X2_EH, X2_EM);
   txt += "\n透明度: 数値を下げると色が濃くなります";

   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, InpCorner);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, InpLegendX);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, InpLegendY);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
     }
   ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, InpLegendSize);
   ObjectSetInteger(0, name, OBJPROP_COLOR, InpLegendColor);
   ObjectSetString(0, name, OBJPROP_TEXT, txt);
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   EventSetTimer(InpRefreshSec);
   RedrawAllBands();
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   DeleteMhdObjects();
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   RedrawAllBands();
  }

//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(id == CHARTEVENT_CHART_CHANGE)
      RedrawAllBands();
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                 const int prev_calculated,
                 const datetime &time[],
                 const double &open[],
                 const double &high[],
                 const double &low[],
                 const double &close[],
                 const long &tick_volume[],
                 const long &volume[],
                 const int &spread[])
  {
   return 0;
  }

//+------------------------------------------------------------------+
