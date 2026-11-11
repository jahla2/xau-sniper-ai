#property strict
#property version   "0.20"
#property description "XAU Sniper AI - demo-first MT5 execution layer"

#include <Trade/Trade.mqh>

CTrade trade;

input string InpAnalyzeUrl             = "http://127.0.0.1:8765/analyze";
input string InpHealthUrl              = "http://127.0.0.1:8765/health";
input bool   InpEnableAutoTrading      = true;
input bool   InpAllowLiveTrading       = false;
input bool   InpUseClaude              = false;
input ulong  InpMagicNumber            = 26011101;
input double InpRiskPercent            = 0.25;
input double InpMinRiskReward          = 2.0;
input double InpMaxSpreadPrice         = 0.50;
input int    InpMaxOpenPositions       = 1;
input double InpMaxDailyLossPct        = 2.0;
input int    InpPollSeconds            = 5;
input int    InpHttpTimeoutMs          = 5000;
input int    InpM1Bars                 = 60;
input int    InpM5Bars                 = 60;
input int    InpM15Bars                = 40;
input int    InpH1Bars                 = 24;
input int    InpPendingExpiryBars      = 3;
input double InpTp1RR                  = 2.0;
input double InpPartialClosePercent    = 50.0;
input int    InpDeviationPoints        = 30;
input int    InpBreakEvenOffsetPoints  = 0;

struct TradeSignal
{
   bool   approved;
   string action;
   string entry_type;
   int    confidence;
   double entry;
   double stop_loss;
   double take_profit_1;
   double take_profit_2;
};

datetime g_last_closed_m1 = 0;
string   g_last_signal_key = "";
bool     g_api_ok = false;

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetAsyncMode(false);

   if(InpRiskPercent <= 0.0 || InpRiskPercent > 5.0)
   {
      Print("XAU Sniper AI: invalid risk percent. Use >0 and <=5.");
      return INIT_PARAMETERS_INCORRECT;
   }

   if(InpPollSeconds < 1)
      return INIT_PARAMETERS_INCORRECT;

   EventSetTimer(InpPollSeconds);

   if((bool)MQLInfoInteger(MQL_TESTER))
   {
      Print("XAU Sniper AI: Strategy Tester detected. WebRequest is unavailable; execution API calls are disabled in tester.");
      g_api_ok = false;
   }
   else
   {
      g_api_ok = CheckApiHealth();
      if(!g_api_ok)
         Print("XAU Sniper AI: API health check failed. Add http://127.0.0.1:8765 to MT5 allowed WebRequest URLs and start FastAPI.");
   }

   if(IsRealAccount() && !InpAllowLiveTrading)
      Print("XAU Sniper AI: REAL account detected. Auto execution is BLOCKED until AllowLiveTrading=true.");

   Print("XAU Sniper AI initialized on ", _Symbol, ". Demo-first auto trading=", InpEnableAutoTrading ? "ON" : "OFF");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTick()
{
   ManageOpenPositions();
}

void OnTimer()
{
   ManageOpenPositions();
   CancelStalePendingOrders();

   if((bool)MQLInfoInteger(MQL_TESTER))
      return;

   datetime closed_m1 = iTime(_Symbol, PERIOD_M1, 1);
   if(closed_m1 <= 0 || closed_m1 == g_last_closed_m1)
      return;

   g_last_closed_m1 = closed_m1;

   if(!g_api_ok)
      g_api_ok = CheckApiHealth();
   if(!g_api_ok)
      return;

   AnalyzeAndMaybeTrade();
}

bool AnalyzeAndMaybeTrade()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
   {
      Print("XAU Sniper AI: SymbolInfoTick failed.");
      return false;
   }

   string payload;
   if(!BuildAnalyzePayload(tick, payload))
   {
      Print("XAU Sniper AI: unable to build analysis payload. Need enough closed candles on all timeframes.");
      return false;
   }

   string response;
   int http_code = HttpPostJson(InpAnalyzeUrl, payload, response);
   if(http_code != 200)
   {
      PrintFormat("XAU Sniper AI: /analyze HTTP %d. Response=%s", http_code, response);
      g_api_ok = false;
      return false;
   }

   TradeSignal signal;
   ResetSignal(signal);
   if(!ParseSignal(response, signal))
   {
      Print("XAU Sniper AI: invalid analyzer response: ", response);
      return false;
   }

   PrintFormat("XAU Sniper AI: action=%s approved=%s confidence=%d entry_type=%s entry=%.2f SL=%.2f TP1=%.2f TP2=%.2f",
               signal.action, signal.approved ? "true" : "false", signal.confidence,
               signal.entry_type, signal.entry, signal.stop_loss,
               signal.take_profit_1, signal.take_profit_2);

   if(!signal.approved || signal.action == "WAIT")
      return true;

   return ExecuteSignal(signal, tick);
}

void ResetSignal(TradeSignal &signal)
{
   signal.approved = false;
   signal.action = "WAIT";
   signal.entry_type = "NONE";
   signal.confidence = 0;
   signal.entry = 0.0;
   signal.stop_loss = 0.0;
   signal.take_profit_1 = 0.0;
   signal.take_profit_2 = 0.0;
}

bool BuildAnalyzePayload(const MqlTick &tick, string &payload)
{
   string m1, m5, m15, h1;
   if(!BuildRatesJson(PERIOD_M1, InpM1Bars, m1)) return false;
   if(!BuildRatesJson(PERIOD_M5, InpM5Bars, m5)) return false;
   if(!BuildRatesJson(PERIOD_M15, InpM15Bars, m15)) return false;
   if(!BuildRatesJson(PERIOD_H1, InpH1Bars, h1)) return false;

   double daily_pnl = CalculateAccountDailyPnl();
   int open_positions = PositionsTotal();
   double spread = tick.ask - tick.bid;

   payload = "{";
   payload += "\"market\":{";
   payload += "\"symbol\":\"" + JsonEscape(_Symbol) + "\",";
   payload += "\"bid\":" + PriceJson(tick.bid) + ",";
   payload += "\"ask\":" + PriceJson(tick.ask) + ",";
   payload += "\"spread\":" + PriceJson(spread) + ",";
   payload += "\"m1\":" + m1 + ",";
   payload += "\"m5\":" + m5 + ",";
   payload += "\"m15\":" + m15 + ",";
   payload += "\"h1\":" + h1;
   payload += "},";

   payload += "\"policy\":{";
   payload += "\"max_risk_pct\":" + DoubleToString(InpRiskPercent, 4) + ",";
   payload += "\"min_rr\":" + DoubleToString(InpMinRiskReward, 2) + ",";
   payload += "\"max_spread\":" + DoubleToString(InpMaxSpreadPrice, 4) + ",";
   payload += "\"max_open_positions\":" + IntegerToString(InpMaxOpenPositions) + ",";
   payload += "\"max_daily_loss_pct\":" + DoubleToString(InpMaxDailyLossPct, 2);
   payload += "},";

   payload += "\"risk\":{";
   payload += "\"balance\":" + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + ",";
   payload += "\"open_positions\":" + IntegerToString(open_positions) + ",";
   payload += "\"daily_pnl\":" + DoubleToString(daily_pnl, 2);
   payload += "},";
   payload += "\"use_claude\":" + (InpUseClaude ? "true" : "false");
   payload += "}";
   return true;
}

bool BuildRatesJson(const ENUM_TIMEFRAMES timeframe, const int requested, string &json)
{
   int need = MathMax(requested, 8);
   MqlRates rates[];
   int copied = CopyRates(_Symbol, timeframe, 1, need, rates); // shift 1 = closed candles only
   if(copied < 8)
      return false;

   ArraySetAsSeries(rates, true);
   json = "[";
   for(int i = copied - 1; i >= 0; --i) // oldest -> newest
   {
      if(i != copied - 1)
         json += ",";

      json += "{";
      json += "\"ts\":" + LongToString((long)rates[i].time) + ",";
      json += "\"open\":" + PriceJson(rates[i].open) + ",";
      json += "\"high\":" + PriceJson(rates[i].high) + ",";
      json += "\"low\":" + PriceJson(rates[i].low) + ",";
      json += "\"close\":" + PriceJson(rates[i].close) + ",";
      json += "\"volume\":" + LongToString((long)rates[i].tick_volume);
      json += "}";
   }
   json += "]";
   return true;
}

int HttpPostJson(const string url, const string body, string &response)
{
   char data[];
   char result[];
   string result_headers;
   string headers = "Content-Type: application/json\r\nAccept: application/json\r\n";

   int copied = StringToCharArray(body, data, 0, WHOLE_ARRAY, CP_UTF8);
   if(copied > 0)
      ArrayResize(data, copied - 1); // remove trailing null byte

   ResetLastError();
   int code = WebRequest("POST", url, headers, InpHttpTimeoutMs, data, result, result_headers);
   if(code == -1)
   {
      int err = GetLastError();
      PrintFormat("XAU Sniper AI: WebRequest POST failed. error=%d url=%s", err, url);
      response = "";
      return -1;
   }

   response = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
   return code;
}

int HttpGet(const string url, string &response)
{
   char data[];
   char result[];
   string result_headers;
   string headers = "Accept: application/json\r\n";

   ResetLastError();
   int code = WebRequest("GET", url, headers, InpHttpTimeoutMs, data, result, result_headers);
   if(code == -1)
   {
      PrintFormat("XAU Sniper AI: WebRequest GET failed. error=%d url=%s", GetLastError(), url);
      response = "";
      return -1;
   }

   response = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
   return code;
}

bool CheckApiHealth()
{
   if((bool)MQLInfoInteger(MQL_TESTER))
      return false;

   string response;
   int code = HttpGet(InpHealthUrl, response);
   bool ok = (code == 200 && StringFind(response, "\"status\":\"ok\"") >= 0);
   if(ok)
      Print("XAU Sniper AI: API connected.");
   return ok;
}

bool ParseSignal(const string json, TradeSignal &signal)
{
   bool approved;
   if(!JsonGetBool(json, "approved", approved))
      return false;
   signal.approved = approved;

   if(!JsonGetString(json, "action", signal.action))
      return false;
   JsonGetString(json, "entry_type", signal.entry_type);
   JsonGetInt(json, "confidence", signal.confidence);

   if(signal.action != "WAIT")
   {
      if(!JsonGetDouble(json, "entry", signal.entry)) return false;
      if(!JsonGetDouble(json, "stop_loss", signal.stop_loss)) return false;
      if(!JsonGetDouble(json, "take_profit_1", signal.take_profit_1)) return false;
      if(!JsonGetDouble(json, "take_profit_2", signal.take_profit_2)) return false;
   }
   return true;
}

bool ExecuteSignal(const TradeSignal &signal, const MqlTick &tick)
{
   if(!InpEnableAutoTrading)
   {
      Print("XAU Sniper AI: signal approved but auto trading is OFF.");
      return false;
   }

   if(!TradingEnvironmentAllowed())
      return false;

   if(HasBotExposure())
   {
      Print("XAU Sniper AI: bot already has an open position or pending order. New signal skipped.");
      return false;
   }

   double spread = tick.ask - tick.bid;
   if(spread > InpMaxSpreadPrice)
   {
      PrintFormat("XAU Sniper AI: spread %.2f > max %.2f. Signal skipped.", spread, InpMaxSpreadPrice);
      return false;
   }

   string key = signal.action + "|" + PriceJson(signal.entry) + "|" + PriceJson(signal.stop_loss) + "|" + PriceJson(signal.take_profit_2);
   if(key == g_last_signal_key)
   {
      Print("XAU Sniper AI: duplicate signal skipped.");
      return false;
   }

   double reference_entry = signal.entry;
   if(signal.entry_type == "MARKET")
      reference_entry = (signal.action == "LONG" ? tick.ask : tick.bid);

   if(!ValidatePriceGeometry(signal.action, reference_entry, signal.stop_loss, signal.take_profit_2))
   {
      Print("XAU Sniper AI: invalid price geometry. Signal skipped.");
      return false;
   }

   double volume = CalculateRiskVolume(reference_entry, signal.stop_loss);
   if(volume <= 0.0)
   {
      Print("XAU Sniper AI: calculated volume is below broker minimum or symbol risk data is unavailable.");
      return false;
   }

   double sl = NormalizeDouble(signal.stop_loss, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
   double tp = NormalizeDouble(signal.take_profit_2, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
   double entry = NormalizeDouble(signal.entry, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
   string comment = "XAU_SNIPER_AI";
   bool sent = false;

   if(signal.entry_type == "MARKET")
   {
      if(signal.action == "LONG")
         sent = trade.Buy(volume, _Symbol, 0.0, sl, tp, comment);
      else if(signal.action == "SHORT")
         sent = trade.Sell(volume, _Symbol, 0.0, sl, tp, comment);
   }
   else if(signal.entry_type == "LIMIT")
   {
      if(signal.action == "LONG")
      {
         if(entry >= tick.ask)
         {
            PrintFormat("XAU Sniper AI: LONG limit %.2f is no longer below ask %.2f; stale/chased entry skipped.", entry, tick.ask);
            return false;
         }
         sent = trade.BuyLimit(volume, entry, _Symbol, sl, tp, ORDER_TIME_GTC, 0, comment);
      }
      else if(signal.action == "SHORT")
      {
         if(entry <= tick.bid)
         {
            PrintFormat("XAU Sniper AI: SHORT limit %.2f is no longer above bid %.2f; stale/chased entry skipped.", entry, tick.bid);
            return false;
         }
         sent = trade.SellLimit(volume, entry, _Symbol, sl, tp, ORDER_TIME_GTC, 0, comment);
      }
   }

   if(!sent || !TradeRetcodeOk())
   {
      PrintFormat("XAU Sniper AI: trade request failed. retcode=%u %s",
                  trade.ResultRetcode(), trade.ResultRetcodeDescription());
      return false;
   }

   g_last_signal_key = key;
   PrintFormat("XAU Sniper AI: order accepted. action=%s type=%s volume=%.2f entry=%.2f SL=%.2f TP2=%.2f order=%I64u deal=%I64u",
               signal.action, signal.entry_type, volume, entry, sl, tp,
               trade.ResultOrder(), trade.ResultDeal());
   return true;
}

bool TradingEnvironmentAllowed()
{
   if(!(bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !(bool)MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      Print("XAU Sniper AI: terminal/EA Algo Trading permission is disabled.");
      return false;
   }

   if(IsRealAccount() && !InpAllowLiveTrading)
   {
      Print("XAU Sniper AI: real-account trade blocked by AllowLiveTrading=false.");
      return false;
   }
   return true;
}

bool IsRealAccount()
{
   return ((ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL);
}

bool ValidatePriceGeometry(const string action, const double entry, const double sl, const double tp)
{
   if(entry <= 0.0 || sl <= 0.0 || tp <= 0.0)
      return false;
   if(action == "LONG")
      return (sl < entry && tp > entry);
   if(action == "SHORT")
      return (sl > entry && tp < entry);
   return false;
}

double CalculateRiskVolume(const double entry, const double sl)
{
   double risk_money = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0;
   double stop_distance = MathAbs(entry - sl);
   double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tick_value <= 0.0)
      tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);

   if(risk_money <= 0.0 || stop_distance <= 0.0 || tick_size <= 0.0 || tick_value <= 0.0)
      return 0.0;

   double loss_per_lot = (stop_distance / tick_size) * tick_value;
   if(loss_per_lot <= 0.0)
      return 0.0;

   double raw = risk_money / loss_per_lot;
   double min_volume = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_volume = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0)
      return 0.0;

   double normalized = MathFloor(raw / step) * step; // floor so we never exceed requested risk
   normalized = NormalizeDouble(normalized, VolumeDigits(step));

   if(normalized < min_volume)
      return 0.0; // do not force broker minimum if it would exceed risk budget
   if(normalized > max_volume)
      normalized = max_volume;

   double margin = 0.0;
   ENUM_ORDER_TYPE side = (sl < entry ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(OrderCalcMargin(side, _Symbol, normalized, entry, margin))
   {
      double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
      if(margin > free_margin * 0.90)
      {
         PrintFormat("XAU Sniper AI: margin %.2f would consume >90%% of free margin %.2f.", margin, free_margin);
         return 0.0;
      }
   }

   return normalized;
}

int VolumeDigits(const double step)
{
   int digits = 0;
   double x = step;
   while(digits < 8 && MathAbs(x - MathRound(x)) > 1e-8)
   {
      x *= 10.0;
      digits++;
   }
   return digits;
}

bool HasBotExposure()
{
   for(int i = PositionsTotal() - 1; i >= 0; --i)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
   }

   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) == _Symbol && (ulong)OrderGetInteger(ORDER_MAGIC) == InpMagicNumber)
         return true;
   }
   return false;
}

void CancelStalePendingOrders()
{
   if(InpPendingExpiryBars <= 0)
      return;

   long max_age = (long)InpPendingExpiryBars * PeriodSeconds(PERIOD_M1);
   datetime now = TimeCurrent();

   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagicNumber) continue;

      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(type != ORDER_TYPE_BUY_LIMIT && type != ORDER_TYPE_SELL_LIMIT &&
         type != ORDER_TYPE_BUY_STOP && type != ORDER_TYPE_SELL_STOP &&
         type != ORDER_TYPE_BUY_STOP_LIMIT && type != ORDER_TYPE_SELL_STOP_LIMIT)
         continue;

      datetime setup = (datetime)OrderGetInteger(ORDER_TIME_SETUP);
      if(setup > 0 && (now - setup) >= max_age)
      {
         if(trade.OrderDelete(ticket) && TradeRetcodeOk())
            PrintFormat("XAU Sniper AI: stale pending order %I64u cancelled.", ticket);
         else
            PrintFormat("XAU Sniper AI: failed to cancel stale order %I64u: %s", ticket, trade.ResultRetcodeDescription());
      }
   }
}

void ManageOpenPositions()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;

   for(int i = PositionsTotal() - 1; i >= 0; --i)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;

      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL);
      double current_volume = PositionGetDouble(POSITION_VOLUME);

      if(open <= 0.0 || sl <= 0.0 || current_volume <= 0.0)
         continue;

      bool already_be = (type == POSITION_TYPE_BUY ? sl >= open : sl <= open);
      if(already_be)
         continue;

      double initial_risk = MathAbs(open - sl);
      double tp1 = (type == POSITION_TYPE_BUY ? open + initial_risk * InpTp1RR : open - initial_risk * InpTp1RR);
      bool tp1_hit = (type == POSITION_TYPE_BUY ? tick.bid >= tp1 : tick.ask <= tp1);
      if(!tp1_hit)
         continue;

      TryPartialClose(ticket, current_volume);

      double be = (type == POSITION_TYPE_BUY ? open + InpBreakEvenOffsetPoints * _Point : open - InpBreakEvenOffsetPoints * _Point);
      be = NormalizeDouble(be, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
      if(!PositionSelectByTicket(ticket))
         continue;
      double current_tp = PositionGetDouble(POSITION_TP);
      if(trade.PositionModify(ticket, be, current_tp) && TradeRetcodeOk())
         PrintFormat("XAU Sniper AI: TP1 reached on %I64u; SL moved to break-even %.2f.", ticket, be);
      else
         PrintFormat("XAU Sniper AI: failed moving %I64u to break-even: %s", ticket, trade.ResultRetcodeDescription());
   }
}

void TryPartialClose(const ulong ticket, const double current_volume)
{
   if(InpPartialClosePercent <= 0.0 || InpPartialClosePercent >= 100.0)
      return;

   ENUM_ACCOUNT_MARGIN_MODE mode = (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
   if(mode != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
   {
      Print("XAU Sniper AI: partial close skipped because account is not hedging; break-even management still applies.");
      return;
   }

   double min_volume = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0) return;

   double close_volume = current_volume * InpPartialClosePercent / 100.0;
   close_volume = MathFloor(close_volume / step) * step;
   close_volume = NormalizeDouble(close_volume, VolumeDigits(step));
   double remainder = NormalizeDouble(current_volume - close_volume, VolumeDigits(step));

   if(close_volume < min_volume || remainder < min_volume)
   {
      Print("XAU Sniper AI: partial close volume/remainder below broker minimum; keeping full position and moving SL only.");
      return;
   }

   if(trade.PositionClosePartial(ticket, close_volume, InpDeviationPoints) && TradeRetcodeOk())
      PrintFormat("XAU Sniper AI: TP1 partial close %.2f lots executed on %I64u.", close_volume, ticket);
   else
      PrintFormat("XAU Sniper AI: partial close failed on %I64u: %s", ticket, trade.ResultRetcodeDescription());
}

bool TradeRetcodeOk()
{
   uint rc = trade.ResultRetcode();
   return (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_DONE_PARTIAL || rc == TRADE_RETCODE_PLACED);
}

double CalculateAccountDailyPnl()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   dt.hour = 0;
   dt.min = 0;
   dt.sec = 0;
   datetime start = StructToTime(dt);

   if(!HistorySelect(start, TimeCurrent()))
      return 0.0;

   double pnl = 0.0;
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; ++i)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0) continue;
      ENUM_DEAL_TYPE type = (ENUM_DEAL_TYPE)HistoryDealGetInteger(ticket, DEAL_TYPE);
      if(type != DEAL_TYPE_BUY && type != DEAL_TYPE_SELL)
         continue;
      pnl += HistoryDealGetDouble(ticket, DEAL_PROFIT);
      pnl += HistoryDealGetDouble(ticket, DEAL_COMMISSION);
      pnl += HistoryDealGetDouble(ticket, DEAL_SWAP);
   }
   return pnl;
}

string PriceJson(const double value)
{
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   return DoubleToString(value, digits);
}

string JsonEscape(string value)
{
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   return value;
}

bool JsonGetBool(const string json, const string key, bool &value)
{
   int pos = JsonValueStart(json, key);
   if(pos < 0) return false;
   string tail = StringSubstr(json, pos, 5);
   if(StringFind(tail, "true") == 0) { value = true; return true; }
   if(StringFind(tail, "false") == 0) { value = false; return true; }
   return false;
}

bool JsonGetString(const string json, const string key, string &value)
{
   int pos = JsonValueStart(json, key);
   if(pos < 0 || StringSubstr(json, pos, 1) != "\"") return false;
   int end = StringFind(json, "\"", pos + 1);
   if(end < 0) return false;
   value = StringSubstr(json, pos + 1, end - pos - 1);
   return true;
}

bool JsonGetDouble(const string json, const string key, double &value)
{
   string raw;
   if(!JsonGetNumberRaw(json, key, raw)) return false;
   if(raw == "null" || raw == "") return false;
   value = StringToDouble(raw);
   return true;
}

bool JsonGetInt(const string json, const string key, int &value)
{
   string raw;
   if(!JsonGetNumberRaw(json, key, raw)) return false;
   value = (int)StringToInteger(raw);
   return true;
}

bool JsonGetNumberRaw(const string json, const string key, string &raw)
{
   int pos = JsonValueStart(json, key);
   if(pos < 0) return false;
   int end = pos;
   int len = StringLen(json);
   while(end < len)
   {
      ushort ch = StringGetCharacter(json, end);
      if(ch == ',' || ch == '}' || ch == ']' || ch == 13 || ch == 10 || ch == 32 || ch == 9)
         break;
      end++;
   }
   raw = StringSubstr(json, pos, end - pos);
   return (StringLen(raw) > 0);
}

int JsonValueStart(const string json, const string key)
{
   string token = "\"" + key + "\"";
   int pos = StringFind(json, token);
   if(pos < 0) return -1;
   pos = StringFind(json, ":", pos + StringLen(token));
   if(pos < 0) return -1;
   pos++;
   int len = StringLen(json);
   while(pos < len)
   {
      ushort ch = StringGetCharacter(json, pos);
      if(ch != 32 && ch != 9 && ch != 13 && ch != 10)
         break;
      pos++;
   }
   return pos;
}
