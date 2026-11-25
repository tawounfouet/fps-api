# BE-000-08 - Domain State Contract Test Matrix

| Champ | Valeur |
|---|---|
| Ticket | BE-000-08 / M0 |
| Date | 2026-11-25 |
| Statut | PLANNED / NOT_EXECUTED |
| Autorite | docs/adr/ADR-0007-domain-state-and-revisions.md |
| Crosswalk | docs/contracts/domain-state-crosswalk.md |
| Total scenarios | 74 |
| Execution | Aucun test applicatif ou de base de donnees n'a ete execute pendant M0 |

## Scenarios de validation

| Test ID | Domaine | Scenario | Resultat attendu | Jalon | Preuve |
|---|---|---|---|---|---|
| ST-001 | Publication | Create Page produces DRAFT | DRAFT persisted and absent from public | M6 | NOT_EXECUTED |
| ST-002 | Publication | Publish DRAFT valid | PUBLISHED with immutable revision and pointer | M6 | NOT_EXECUTED |
| ST-003 | Publication | Archive PUBLISHED | ARCHIVED and public 404 | M6 | NOT_EXECUTED |
| ST-004 | Publication | Restore ARCHIVED | DRAFT and public 404 until republish | M6 | NOT_EXECUTED |
| ST-005 | Publication | Publish ARCHIVED directly | Business validation error; no public mutation | M6 | NOT_EXECUTED |
| ST-006 | Publication | Republish PUBLISHED | New revision/pointer; no draft data leak | M6 | NOT_EXECUTED |
| ST-007 | Publication | Edit published working copy | Public still serves prior snapshot | M6 | NOT_EXECUTED |
| ST-008 | Publication | Full workflow IN_REVIEW requested in MVP | Not a valid persisted MVP status | M6 | NOT_EXECUTED |
| ST-009 | Contact | Submit valid Contact with DB commit | workflow_status=RECEIVED; HTTP 201 | M2/M4 | NOT_EXECUTED |
| ST-010 | Contact | Contact DB failure | No 201 and no Email call | M2/M4 | NOT_EXECUTED |
| ST-011 | Contact | Provider unavailable after commit | Contact survives and workflow remains RECEIVED | M2/M4 | NOT_EXECUTED |
| ST-012 | Contact | MarkContacted while email PENDING | CONTACTED independent of delivery | M2/M4 | NOT_EXECUTED |
| ST-013 | Contact | Close CONTACTED | CLOSED and audit recorded | M2/M4 | NOT_EXECUTED |
| ST-014 | Contact | Reopen CLOSED | CONTACTED only via command | M2/M4 | NOT_EXECUTED |
| ST-015 | Contact | Archive CLOSED | ARCHIVED with historical trace | M2/M4 | NOT_EXECUTED |
| ST-016 | Contact | Attempt ACCEPTED by provider | dispatch ACCEPTED, delivery projection not DELIVERED | M2/M4 | NOT_EXECUTED |
| ST-017 | Contact | Verified delivered webhook | Append receipt event, derived DELIVERED | M2/M4 | NOT_EXECUTED |
| ST-018 | Contact | Verified bounce after ACCEPTED | Historical acceptance preserved, derived FAILED | M2/M4 | NOT_EXECUTED |
| ST-019 | Contact | Retry transport after ambiguous timeout | Stable same-intent key/payload, no duplicate lead | M2/M4 | NOT_EXECUTED |
| ST-020 | Contact | NEW/DELIVERING written to workflow_status | Rejected as non-canonical | M2/M4 | NOT_EXECUTED |
| ST-021 | Published snapshot | Publish creates revision and pointer transactionally | Both committed or both rolled back | M2/M6/M7 | NOT_EXECUTED |
| ST-022 | Published snapshot | Published revision FK targets another page | Reject cross-resource pointer | M2/M6/M7 | NOT_EXECUTED |
| ST-023 | Published snapshot | Draft edit after publish | Snapshot bytes/JSON stay unchanged | M2/M6/M7 | NOT_EXECUTED |
| ST-024 | Published snapshot | No published pointer with PUBLISHED state | Safe error and no working-copy leak | M2/M6/M7 | NOT_EXECUTED |
| ST-025 | Published snapshot | Archive preserves pointer for history | Status gates visibility with 404 | M2/M6/M7 | NOT_EXECUTED |
| ST-026 | Published snapshot | Restore leaves old published pointer | Public 404 until explicit publish | M2/M6/M7 | NOT_EXECUTED |
| ST-027 | Published snapshot | Concurrent two publishes same expected_version | Exactly one wins, other 409 | M2/M6/M7 | NOT_EXECUTED |
| ST-028 | Published snapshot | Next.js invalidation fails after commit | Snapshot valid; durable revalidation intent pending | M2/M6/M7 | NOT_EXECUTED |
| ST-029 | Locale and slugs | Duplicate Page locale/slug | DB/app uniqueness rejects | M6/M8 | NOT_EXECUTED |
| ST-030 | Locale and slugs | Same slug Page vs Blog in separate namespaces | Allowed when routing disjoint | M6/M8 | NOT_EXECUTED |
| ST-031 | Locale and slugs | Duplicate group+locale | Rejected per resource type | M6/M8 | NOT_EXECUTED |
| ST-032 | Locale and slugs | One translation group mixes Page and Blog | Rejected | M6/M8 | NOT_EXECUTED |
| ST-033 | Locale and slugs | Route /en/... missing translation | Localized 404, no French fallback | M6/M8 | NOT_EXECUTED |
| ST-034 | Locale and slugs | Reserved frontend Page slug | Rejected before publish | M6/M8 | NOT_EXECUTED |
| ST-035 | Locale and slugs | Change published slug | Redirect decision recorded; no silent cross-locale switch | M6/M8 | NOT_EXECUTED |
| ST-036 | Media | CreateUploadIntent before bytes | Media UPLOADING, intent PENDING_UPLOAD distinct | M5/M6 | NOT_EXECUTED |
| ST-037 | Media | Successful PUT only | Does not imply READY | M5/M6 | NOT_EXECUTED |
| ST-038 | Media | HEAD exists but spoofed MIME | Reject, status not READY | M5/M6 | NOT_EXECUTED |
| ST-039 | Media | Corrupt image bytes | PROCESSING -> FAILED | M5/M6 | NOT_EXECUTED |
| ST-040 | Media | Valid final object with computed SHA-256 | PROCESSING -> READY | M5/M6 | NOT_EXECUTED |
| ST-041 | Media | Publish with Media PROCESSING | Validation rejection | M5/M6 | NOT_EXECUTED |
| ST-042 | Media | Publish with Media READY lacking locale alt | Reject if not decorative | M5/M6 | NOT_EXECUTED |
| ST-043 | Media | Publish with decorative=true and no alt | Allowed if context/format valid | M5/M6 | NOT_EXECUTED |
| ST-044 | Media | Archive referenced Media | Historical published reference kept; block new selection | M5/M6 | NOT_EXECUTED |
| ST-045 | Media | Hard delete Media referenced in published snapshot | Reject while in use | M5/M6 | NOT_EXECUTED |
| ST-046 | Media | Restore Media ARCHIVED | Only when object present and verified | M5/M6 | NOT_EXECUTED |
| ST-047 | Revision lifecycle | Edit working copy ordinary save | No automatic revision by default | M2/M6 | NOT_EXECUTED |
| ST-048 | Revision lifecycle | Publish | Immutable revision inserted | M2/M6 | NOT_EXECUTED |
| ST-049 | Revision lifecycle | Archive | Historical snapshot/audit permitted; published pointer unchanged | M2/M6 | NOT_EXECUTED |
| ST-050 | Revision lifecycle | Restore | Historical snapshot/audit permitted; public remains invisible | M2/M6 | NOT_EXECUTED |
| ST-051 | Revision lifecycle | Old revision UPDATE attempt | Rejected | M2/M6 | NOT_EXECUTED |
| ST-052 | Revision lifecycle | Duplicate version_number for resource | Unique constraint rejects | M2/M6 | NOT_EXECUTED |
| ST-053 | Revision lifecycle | Publish points to archival snapshot | Rejected, requires publish-approved revision | M2/M6 | NOT_EXECUTED |
| ST-054 | Revision lifecycle | Stale expected_version | 409 CONCURRENT_MODIFICATION | M2/M6 | NOT_EXECUTED |
| ST-055 | Menus & localized data | Two navigations same code+locale | Uniqueness rejects | M6/M8 | NOT_EXECUTED |
| ST-056 | Menus & localized data | Navigation item parent cycle | Rejected | M6/M8 | NOT_EXECUTED |
| ST-057 | Menus & localized data | Public menu links unpublished page | Link omitted/rejected by publication validation | M6/M8 | NOT_EXECUTED |
| ST-058 | Menus & localized data | Category labels contain FR and EN | Persist as JSONB labels by code | M6/M8 | NOT_EXECUTED |
| ST-059 | Menus & localized data | Taxonomy API slug differs from code in MVP | Reject/no automatic localized slug | M6/M8 | NOT_EXECUTED |
| ST-060 | Menus & localized data | Media alt/caption languages | JSONB keyed by locale | M6/M8 | NOT_EXECUTED |
| ST-061 | Menus & localized data | Hreflang includes EN draft | Omit unavailable EN | M6/M8 | NOT_EXECUTED |
| ST-062 | Menus & localized data | Translation is outdated with revision evidence | Derived OUTDATED freshness; public published resource stays | M6/M8 | NOT_EXECUTED |
| ST-063 | Menus & localized data | Translation freshness without source-revision evidence | Unknown; never assert CURRENT or OUTDATED | M6/M8 | NOT_EXECUTED |
| ST-064 | Identity and access | OIDC token valid, FPS User SUSPENDED | 403 for Admin route | M3 | NOT_EXECUTED |
| ST-065 | Identity and access | OIDC token valid, FPS User DISABLED | 403 for Admin route | M3 | NOT_EXECUTED |
| ST-066 | Identity and access | OIDC token valid, FPS User ACTIVE with permission | Allowed | M3 | NOT_EXECUTED |
| ST-067 | Identity and access | OIDC role claim SUPER_ADMIN without DB role | No escalation | M3 | NOT_EXECUTED |
| ST-068 | Identity and access | Admin media upload with MANAGE_MEDIA | Authorized if other guards pass | M3 | NOT_EXECUTED |
| ST-069 | Identity and access | Admin media upload with only MEDIA_UPLOAD claim | Reject; unregistered code | M3 | NOT_EXECUTED |
| ST-070 | Identity and access | Remove last ACTIVE SuperAdmin | Reject transaction | M3 | NOT_EXECUTED |
| ST-071 | Identity and access | Concurrent two SuperAdmins both self-demote | At least one remains ACTIVE+SuperAdmin | M3 | NOT_EXECUTED |
| ST-072 | Identity and access | Disable final ACTIVE SuperAdmin | Reject transaction | M3 | NOT_EXECUTED |
| ST-073 | Identity and access | Create User with INVITED persisted as UserStatus | Not supported MVP | M3 | NOT_EXECUTED |
| ST-074 | Identity and access | Switch SUSPENDED to ACTIVE without authorized action | Rejected | M3 | NOT_EXECUTED |

## Protocole de collecte de preuve future

Chaque execution devra fournir `test_id`, `commit_sha`, `environment`, `executed_at_utc`, `test_command`, `assertion_expected`, `result_observed`, `verdict`, `evidence_url`, `owner` et les references de donnees **synthetiques**, sans PII.

- Tests transactionnels avec PostgreSQL reel pour les contraintes uniques, les pointeurs de publication, les revisions et le dernier SuperAdmin. SQLite n'est pas une preuve suffisante.
- Tests HTTP sur l'OpenAPI genere par FastAPI (M1+), pas uniquement sur le draft JSON M0.
- Tests echec injection pour publication et envoi Contact: crash avant commit, apres commit, timeout provider, double claim worker (BE-000-09).
- Tests medias contre FakeObjectStoragePort puis R2 dans un environnement de qualification autorise, sans bucket ou secrets de production.
- Tests i18n sur FR/EN avec hreflang, slug et statut publie; pas d'hypothese de fallback.
- Tests IAM avec IdentityProvider mock et DB locale ACTIVE/SUSPENDED/DISABLED; race condition sur les changements roles.
- Retention Contact, transfert Email et conformite restent des gates distincts et obligatoires avant donnees reelles.

## Criteres de sortie documentaire M0

- [x] 74 cas nommes avec assertion et jalon.
- [x] Couverture des cinq use cases critiques PublishPage, SubmitContact, CreatePageTranslation, MediaReady, AssignRole.
- [x] Cas negatives : status mix, cross-resource revision FK, stale version, unpublished leak, locale fallback, last SuperAdmin race.
- [ ] Preuves de runs valides : **aucune**; relever sous M2/M3/M4/M5/M6/M7/M8.
- [ ] Schema et migrations verifies : **aucun**; ne pas marquer tests PASS a la fusion du document.

**Les 74 tests sont planifies, et non executes.**
