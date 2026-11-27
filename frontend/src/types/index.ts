export type Overview = {
  total_transactions: number; processed_transactions: number; flagged_transactions: number;
  active_alerts: number; critical_alerts: number; confirmed_fraud_cases: number;
  suspected_fraud_amount: number; average_risk_score: number; estimated_loss_prevented: number | null;
  estimated_loss_prevented_note: string; detection_rate: number; data_mode: string;
}
export type Transaction = {
  transaction_id: string; customer_id: string; amount: number; currency: string; merchant_id: string;
  merchant_category: string; timestamp: string; processing_status: string; fraud_probability: number | null;
  anomaly_score: number | null; risk_score: number | null; risk_category: string | null; decision: string | null;
  model_version?: string;
}
export type Alert = {
  alert_id: string; transaction_id: string; customer_id: string; severity: string; risk_score: number;
  status: string; triggered_rules: string[]; explanation: Record<string, unknown>; assigned_to: string | null;
  created_at: string;
}
