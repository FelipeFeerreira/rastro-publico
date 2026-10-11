import type {
  AssistantAnswer,
  AuthUser,
  CampusDashboard,
  ComparisonResponse,
  ContractDetail,
  ContractSummary,
  Coverage,
  EntitySummary,
  Evidence,
  Finding,
  Investigation,
  Municipality,
  Page,
  Payment,
  Person,
  PersonDetail,
  ProcurementDetail,
  ProcurementSummary,
  SalarySource,
  SearchResponse,
  Source,
  State,
  Suggestion,
  SupplierSummary,
  Token,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface FetchOptions extends RequestInit {
  token?: string | null;
  next?: { revalidate?: number; tags?: string[] };
}

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { token, headers, next, ...rest } = options;
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
      ...(next ? { next } : { cache: rest.method && rest.method !== "GET" ? "no-store" : "no-store" }),
    });
  } catch {
    throw new ApiError(
      "Não foi possível conectar ao serviço de dados. Verifique se a API está no ar.",
      0,
    );
  }

  if (!response.ok) {
    let detail = `Erro ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* resposta não-JSON */
    }
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const str = search.toString();
  return str ? `?${str}` : "";
}

// --- Busca ---
export function search(
  params: {
    q: string;
    types?: string;
    page?: number;
    page_size?: number;
    uf?: string;
    year?: number;
  },
  token?: string | null,
) {
  return apiFetch<SearchResponse>(`/search${qs(params)}`, { token });
}

export function suggest(q: string) {
  return apiFetch<Suggestion[]>(`/search/suggest${qs({ q })}`);
}

// --- Contratações e contratos ---
export function listProcurements(params: Record<string, string | number | undefined>) {
  return apiFetch<Page<ProcurementSummary>>(`/contratacoes${qs(params)}`);
}

export function getProcurement(id: string | number) {
  return apiFetch<ProcurementDetail>(`/contratacoes/${id}`);
}

export function getContract(id: string | number) {
  return apiFetch<ContractDetail>(`/contratos/${id}`);
}

export function listContracts(params: Record<string, string | number | undefined>) {
  return apiFetch<Page<ContractSummary>>(`/contratos${qs(params)}`);
}

export function getCampus(uasg: string) {
  return apiFetch<CampusDashboard>(`/campus/${uasg}`);
}

// --- Fornecedores ---
export function listSuppliers(params: Record<string, string | number | undefined>) {
  return apiFetch<Page<SupplierSummary>>(`/fornecedores${qs(params)}`);
}

export function getSupplier(id: string | number) {
  return apiFetch<SupplierSummary>(`/fornecedores/${id}`);
}

export function getSupplierFindings(id: string | number) {
  return apiFetch<Finding[]>(`/fornecedores/${id}/achados`);
}

export function listSupplierContracts(id: string | number, page = 1) {
  return apiFetch<Page<ContractSummary>>(`/fornecedores/${id}/contratos${qs({ page })}`);
}

export function listEntityProcurements(id: string | number, page = 1) {
  return apiFetch<Page<ProcurementSummary>>(`/orgaos/${id}/contratacoes${qs({ page })}`);
}

export function listEntityContracts(id: string | number, page = 1) {
  return apiFetch<Page<ContractSummary>>(`/orgaos/${id}/contratos${qs({ page })}`);
}

// --- Órgãos e territórios ---
export function listEntities(params: Record<string, string | number | undefined>) {
  return apiFetch<Page<EntitySummary>>(`/orgaos${qs(params)}`);
}

export function getEntity(id: string | number) {
  return apiFetch<EntitySummary>(`/orgaos/${id}`);
}

export function listStates() {
  return apiFetch<State[]>(`/estados`, { next: { revalidate: 3600 } });
}

export function getMunicipality(ibge: string) {
  return apiFetch<
    Municipality & {
      uf: string | null;
      state_name: string | null;
      procurement_count: number;
      estimated_total: number;
    }
  >(`/municipios/${ibge}`);
}

// --- Fontes e cobertura ---
export function listSources() {
  return apiFetch<Source[]>(`/sources`, { next: { revalidate: 300 } });
}

export function getCoverage() {
  return apiFetch<Coverage>(`/meta/coverage`, { next: { revalidate: 60 } });
}

// --- Análise e achados ---
export function listFindings(params: Record<string, string | number | undefined>) {
  return apiFetch<Page<Finding> & { aviso?: string }>(`/achados${qs(params)}`);
}

export function getFinding(publicId: string) {
  return apiFetch<Finding>(`/achados/${publicId}`);
}

export function comparePrices(payload: Record<string, unknown>) {
  return apiFetch<ComparisonResponse>(`/analise/comparacao`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// --- Pagamentos (execução financeira) ---
export function listPayments(params: Record<string, string | number | undefined>) {
  return apiFetch<Page<Payment>>(`/pagamentos${qs(params)}`);
}

export function getContractPayments(contractId: string | number) {
  return apiFetch<Payment[]>(`/contratos/${contractId}/pagamentos`);
}

// --- Servidores e remuneração ---
export function listServidores(params: Record<string, string | number | undefined>) {
  return apiFetch<Page<Person>>(`/servidores${qs(params)}`);
}

export function getServidor(id: string | number) {
  return apiFetch<PersonDetail>(`/servidores/${id}`);
}

export function listSalarySources() {
  return apiFetch<SalarySource[]>(`/salarios/fontes`, { next: { revalidate: 60 } });
}

// --- Assistente ---
export function askAssistant(question: string) {
  return apiFetch<AssistantAnswer>(`/assistente/perguntar`, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

// --- Autenticação ---
export function register(payload: { email: string; full_name: string; password: string }) {
  return apiFetch<AuthUser>(`/auth/registrar`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(payload: { email: string; password: string }) {
  return apiFetch<Token>(`/auth/login`, { method: "POST", body: JSON.stringify(payload) });
}

export function me(token: string) {
  return apiFetch<AuthUser>(`/auth/eu`, { token });
}

// --- Investigações ---
export function listInvestigations(token: string) {
  return apiFetch<Investigation[]>(`/investigacoes`, { token });
}

export function createInvestigation(
  token: string,
  payload: { title: string; description?: string; tags?: string[] },
) {
  return apiFetch<Investigation>(`/investigacoes`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export function getInvestigation(token: string, publicId: string) {
  return apiFetch<Investigation>(`/investigacoes/${publicId}`, { token });
}

export function addEvidence(
  token: string,
  publicId: string,
  payload: Record<string, unknown>,
) {
  return apiFetch<Evidence>(`/investigacoes/${publicId}/evidencias`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export function getReport(token: string, publicId: string) {
  return apiFetch<Record<string, unknown>>(`/investigacoes/${publicId}/relatorio`, { token });
}

export function reportPdfUrl(publicId: string) {
  return `${API_BASE_URL}/investigacoes/${publicId}/relatorio.pdf`;
}
