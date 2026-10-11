export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface State {
  id: number;
  ibge_code: string;
  uf: string;
  name: string;
}

export interface Municipality {
  id: number;
  ibge_code: string;
  name: string;
  state_id: number;
  uf?: string | null;
}

export interface EntitySummary {
  id: number;
  cnpj: string | null;
  uasg: string | null;
  name: string;
  acronym: string | null;
  sphere: string;
  power: string;
  municipality_id: number | null;
  state_id: number | null;
}

export interface SupplierSummary {
  id: number;
  name: string;
  document: string;
  document_type: string | null;
  is_individual: boolean;
  contract_count?: number;
  total_contract_value?: number | null;
  procurement_count?: number;
}

export interface ProcurementItem {
  id: number;
  item_number: number;
  description: string;
  kind: string;
  unit: string | null;
  quantity: number | null;
  unit_price_estimated: number | null;
  total_estimated: number | null;
  judgment_criteria: string | null;
  situation: string | null;
  category_key: string | null;
}

export interface ProcurementResult {
  id: number;
  item_id: number;
  supplier_id: number | null;
  supplier_name: string | null;
  supplier_document: string | null;
  unit_price: number | null;
  quantity: number | null;
  total_price: number | null;
  result_date: string | null;
  status: string | null;
  source_url: string | null;
}

export interface ProcurementSummary {
  id: number;
  pncp_control_number: string;
  number: string | null;
  object_description: string;
  modality: string;
  modality_name: string | null;
  status: string;
  status_name: string | null;
  estimated_total: number | null;
  approved_total: number | null;
  published_at: string | null;
  entity: EntitySummary | null;
  municipality: Municipality | null;
  source_url: string | null;
}

export interface ProcurementDetail extends ProcurementSummary {
  process_number: string | null;
  additional_info: string | null;
  is_price_registry: boolean;
  is_parliamentary_amendment: boolean | null;
  dispute_mode_name: string | null;
  proposal_open_at: string | null;
  proposal_close_at: string | null;
  source_updated_at: string | null;
  collected_at: string | null;
  origin_system_link: string | null;
  items: ProcurementItem[];
  results: ProcurementResult[];
  source?: Source | null;
}

export interface Amendment {
  id: number;
  term_number: string | null;
  amendment_type: string | null;
  value_added: number | null;
  value_reduced: number | null;
  new_value: number | null;
  new_end_date: string | null;
  signed_at: string | null;
  description: string | null;
  source_url: string | null;
}

export interface ContractSummary {
  id: number;
  pncp_control_number: string | null;
  number: string | null;
  object_description: string;
  global_value: number | null;
  initial_value: number | null;
  signed_at: string | null;
  effective_from: string | null;
  effective_until: string | null;
  status: string;
  supplier: SupplierSummary | null;
  entity: EntitySummary | null;
  source_url: string | null;
  paid_value?: number | string | null;
}

export interface PaymentSummary {
  empenhado: number | string;
  liquidado: number | string;
  pago: number | string;
  count: number;
}

export interface Payment {
  id: number;
  contract_id: number | null;
  stage: string;
  value: number | string;
  reference_date: string | null;
  external_id: string | null;
  description: string | null;
  source_system: string;
  source_url: string | null;
  supplier_id: number | null;
}

export interface ContractDetail extends ContractSummary {
  process_number: string | null;
  published_at: string | null;
  amendments: Amendment[];
  payment_summary?: PaymentSummary | null;
  source?: Source | null;
}

export interface CampusTotals {
  contracts: number;
  suppliers: number;
  first_contract_date: string | null;
  last_contract_date: string | null;
  last_collection_at: string | null;
}

export interface CampusFinancials {
  contracted: number | string;
  committed: number | string;
  liquidated: number | string;
  paid: number | string;
  payment_events: number;
}

export interface CampusDashboard {
  entity: EntitySummary;
  uasg: string;
  municipality_name: string | null;
  uf: string | null;
  is_federal: boolean;
  totals: CampusTotals;
  financials: CampusFinancials;
  source: Source | null;
  notes: string[];
}

export interface MunicipalExpense {
  id: number;
  municipality_id: number;
  entity_id: number | null;
  entity_name: string | null;
  supplier_id: number | null;
  supplier_name: string | null;
  supplier_document: string | null;
  empenho_number: string | null;
  stage: string;
  value: number | string | null;
  event_year: number | null;
  event_month: number | null;
  month_name: string | null;
  event_date: string | null;
  description: string | null;
  source_url: string | null;
  collected_at: string | null;
}

export interface MunicipalCoverage {
  first_date: string | null;
  last_date: string | null;
  last_collected_at: string | null;
  months_by_year: Record<string, number[]>;
  partial_years: number[];
}

export interface MunicipalExpenseTotals {
  records: number;
  empenhado: number | string;
  liquidado: number | string;
  pago: number | string;
  reforco: number | string;
  anulacao: number | string;
  committed_net: number | string;
  coverage: MunicipalCoverage | null;
}

export interface MunicipalInstitutionTotals {
  entity_id: number | null;
  entity_name: string | null;
  records: number;
  empenhado: number | string;
  liquidado: number | string;
  pago: number | string;
  reforco: number | string;
  anulacao: number | string;
  committed_net: number | string;
}

export interface Remuneration {
  id: number;
  reference_year: number | null;
  reference_month: number | null;
  gross_amount: number | null;
  net_amount: number | null;
  deductions: number | null;
  reference_date: string | null;
  source_url: string | null;
}

export interface Person {
  id: number;
  name: string;
  masked_document: string | null;
  entity_id: number | null;
  entity_name: string | null;
  role_title: string | null;
  source_url: string | null;
  latest_gross: number | null;
  latest_net: number | null;
  latest_reference_year: number | null;
  latest_reference_month: number | null;
}

export interface PersonDetail extends Person {
  remunerations: Remuneration[];
}

export interface SalarySource {
  code: string;
  name: string;
  status: string;
  supports_salary: boolean;
  credentials_required: boolean;
  credentials_present: boolean;
  note: string;
}

export interface PriceClassification {
  status: string;
  label: string;
  explanation: string;
  percent_difference: number | null;
}

export interface ComparisonResponse {
  classification?: PriceClassification;
  compared_value?: number | null;
  sample_size: number;
  conclusive: boolean;
  unit: string | null;
  distribution: {
    count: number;
    median: number | null;
    p25: number | null;
    p75: number | null;
    iqr: number | null;
    min: number | null;
    max: number | null;
  };
  methodology: string;
  limitations: string;
  records: Array<{
    unit_price: number | null;
    unit: string | null;
    supplier: string | null;
    source_url?: string | null;
  }>;
}

export interface Source {
  id: number;
  code: string;
  name: string;
  description: string | null;
  homepage_url: string;
  api_documentation_url: string | null;
  license_name: string | null;
  license_url: string | null;
  status: string;
  requires_authentication: boolean;
  coverage_description: string | null;
  last_success_at: string | null;
  last_checked_at: string | null;
}

export interface SearchHit {
  type: string;
  id: number;
  title: string;
  subtitle: string | null;
  description: string | null;
  value: string | null;
  date: string | null;
  location: string | null;
  url: string | null;
  source_url: string | null;
  score: number;
  extra: Record<string, unknown>;
}

export interface SearchGroup {
  type: string;
  label: string;
  total: number;
  items: SearchHit[];
}

export interface SearchResponse {
  query: string;
  total: number;
  page: number;
  page_size: number;
  took_ms: number;
  groups: SearchGroup[];
}

export interface Suggestion {
  type: string;
  id: number;
  label: string;
  subtitle: string | null;
  url: string | null;
}

export interface Finding {
  id: number;
  public_id: string;
  status: string;
  severity: string;
  title: string;
  summary: string;
  explanation: string | null;
  methodology: string | null;
  limitations: string | null;
  metrics: Record<string, unknown> | null;
  evidence: unknown[] | null;
  source_records: Array<Record<string, unknown>> | null;
  confidence: number | null;
  rule_code: string | null;
  entity_id: number | null;
  municipality_id: number | null;
  supplier_id: number | null;
  procurement_id: number | null;
  contract_id: number | null;
  created_at: string;
  updated_at: string;
  review_history: Array<Record<string, unknown>> | null;
}

export interface Coverage {
  contratacoes: number;
  contratos: number;
  fornecedores: number;
  resultados_preco: number;
  aviso: string;
}

export interface AssistantAnswer {
  intent: string;
  answer: string;
  grounded: boolean;
  computed: Record<string, unknown> | null;
  citations: Array<Record<string, string | null>>;
  limitations: string[];
  provider: string;
}

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Evidence {
  id: number;
  investigation_id: number;
  kind: string;
  title: string;
  note: string | null;
  reference_type: string | null;
  reference_id: string | null;
  source_url: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export interface Investigation {
  id: number;
  public_id: string;
  title: string;
  description: string | null;
  status: string;
  tags: string[] | null;
  scope: Record<string, unknown> | null;
  is_private: boolean;
  created_at: string;
  updated_at: string;
  evidence_items?: Evidence[];
}
