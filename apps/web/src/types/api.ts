/**
 * Hand-written, stable aliases over the generated OpenAPI schema types.
 *
 * src/types/api.generated.ts is regenerated from the backend's real Pydantic
 * response models (npm run generate:api-types) — never edit it by hand, and
 * never hand-write a type here that duplicates a backend shape. This file
 * only gives the generated schema's (sometimes verbose, auto-disambiguated)
 * names a short, stable name to import elsewhere.
 */
import type { components } from "./api.generated";

type Schemas = components["schemas"];

// Winning Profile Hypothesis™ / capture package
export type Solicitation = Schemas["SolicitationResponse"];
export type EvidenceDocument = Schemas["cios__api__v1__endpoints__winning_profile__DocumentResponse"];
export type ProfileAttribute = Schemas["ProfileAttributeResponse"];
export type Profile = Schemas["ProfileResponse"];
export type Ranking = Schemas["AlignmentResponse"];
export type Assessment = Schemas["AssessmentResponse"];
export type Intelligence = Schemas["IntelligenceResponse"];
export type CapturePackage = Schemas["CapturePackageResponse"];
export type CapturePackageStatus = Schemas["CapturePackageStatus"];

// Knowledge Vault
export type KnowledgeDocument = Schemas["cios__api__v1__endpoints__knowledge_vault__DocumentResponse"];
export type SearchResult = Schemas["SearchResultItem"];

// Opportunity Intelligence
export type Opportunity = Schemas["OpportunityResponse"];
export type AnalyzeOpportunityResponse = Schemas["AnalyzeOpportunityResponse"];
