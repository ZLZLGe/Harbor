package main

import (
	"bytes"
	"compress/zlib"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"regexp"
	"strconv"
	"strings"
)

type includedRow struct {
	StudyID                 string `json:"study_id"`
	ShortCitation           string `json:"short_citation"`
	StudyDesign             string `json:"study_design"`
	PopulationScope         string `json:"population_scope"`
	DurationWeeks           string `json:"duration_weeks"`
	ComparatorType          string `json:"comparator_type"`
	PrimaryOutcomeDirection string `json:"primary_outcome_direction"`
}

type referenceTarget struct {
	DOI                 string `json:"doi"`
	Title               string `json:"title"`
	Journal             string `json:"journal"`
	Year                string `json:"year"`
	FirstAuthorLastName string `json:"first_author_last_name"`
}

type catalogPayload struct {
	SnapshotID       string                     `json:"snapshot_id"`
	IncludedRows     []includedRow              `json:"included_rows"`
	ReferenceTargets map[string]referenceTarget `json:"reference_targets"`
}

const encryptedBlob = "M5rv7QA74Gh1ztbCw61yBtD/UT85a5AmyylacMmLGUCpqxiZVrnFvE8Gu4dznnICzgOeKTjYp19hRLoTZKmRXHWBv+1eIV16bCwre1g1wx5adizOZEEBdcsqsy6wWgM8/GKGfpAq+mqwYh+rtj9g6HUZu4DPQq4mRaSGMP9m/7HFq74fSH58Mevhhdg2CDXWbMxuVBFcAyPiJJD77UbbPSY/cv6HY/tJM/+/yv90ZjjYavXRnwYH+G2kOoWbdlVD0/tXOMDyEn8Uh+6c/Gv5gxQgvN22LKzmRfS7kuThg207hoycXsjaanfp9mTSEAwcJYLX+ZCNcrm8YchX96jGBZLNmVORy+MxoMGJRnQArQhLFL3h7Y4IWq4pJPBOXqinPgmY6m66+pTqnBeBUe12fXKFJBQU5MtkfWAOT/UQF96KTWmPskz5axQ4uRigWDj7+PEXLwr/bZmGDbnofUwvYWqPNvuNDlJMQbyKxcRBXvtF97HGYDDwXUrGcS3RJfnEATPHNUssSjUUyLqH2iO1NkIcgyNEBwywTljtilnB+bmE5Wp035PowJ0O2Bx5XyXfRcbfTvOh3VH4GrkQVVkDUluKOtmnRvhi7CxNlVf0hTWtWyVkFzHgfYu2IcSMNaL/MrKEnfAcf+RpJ6ic4TUvGTyZJTU/nlS8YFk9ytNtH8qX5Os95w1G+srNGWBR29to1LmE4togVJjDWzrvUIXrSWczXqELSMAymoq3YkxZHwhUX1ol/gadnXw28wNcjX/7Bl4eo8MPO7iASvvzfr8VYF8TxYVgzL5Da55ZfcKQrmdrn91bTMaTD5Bf+tokB7tDEiRvbhgLzV+QHByemAcJgAux5alGWWpxRHkvlAgz5d1gIP6+Mzd7F07qiiiLit7TopbyZlgB+VPpgcKUR7LZqu5FWCwLljLrYMWLSTKFXExxIP7fOoJuWARRuvsKNF0tIdG9m41qEpbAN+N8uAivgHWNFvmbNvW5r4vlmtZz5OsjzJyj5D0KtwbIpWMjWkW6+2ul9v6yo8f77u/jNSX+1wbb/qId//I1IJphdtE="
const xorKey = "K@*xMT;XyH)H#n<s2peT"

var nonAlphaNumeric = regexp.MustCompile(`[^a-z0-9]+`)
var servicePayload = mustLoadPayload()
var includedByID = indexIncludedRows(servicePayload.IncludedRows)
var eligibleSet = makeSet(collectEligibleIDs(servicePayload.IncludedRows))

func mustLoadPayload() catalogPayload {
	encoded, err := base64.StdEncoding.DecodeString(encryptedBlob)
	if err != nil {
		log.Fatalf("decode blob: %v", err)
	}

	keyBytes := []byte(xorKey)
	for i := range encoded {
		encoded[i] ^= keyBytes[i%len(keyBytes)]
	}

	reader, err := zlib.NewReader(bytes.NewReader(encoded))
	if err != nil {
		log.Fatalf("zlib reader: %v", err)
	}
	defer reader.Close()

	plain, err := io.ReadAll(reader)
	if err != nil {
		log.Fatalf("inflate payload: %v", err)
	}

	var payload catalogPayload
	if err := json.Unmarshal(plain, &payload); err != nil {
		log.Fatalf("parse payload: %v", err)
	}
	return payload
}

func collectEligibleIDs(rows []includedRow) []string {
	ids := make([]string, 0, len(rows))
	for _, row := range rows {
		ids = append(ids, row.StudyID)
	}
	return ids
}

func indexIncludedRows(rows []includedRow) map[string]includedRow {
	result := make(map[string]includedRow, len(rows))
	for _, row := range rows {
		result[row.StudyID] = row
	}
	return result
}

func makeSet(values []string) map[string]struct{} {
	result := make(map[string]struct{}, len(values))
	for _, value := range values {
		result[value] = struct{}{}
	}
	return result
}

func normalizeText(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	value = nonAlphaNumeric.ReplaceAllString(value, " ")
	return strings.Join(strings.Fields(value), " ")
}

func normalizeDOI(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	value = strings.TrimPrefix(value, "https://doi.org/")
	value = strings.TrimPrefix(value, "http://doi.org/")
	value = strings.TrimPrefix(value, "doi:")
	return strings.TrimSpace(value)
}

func stringValue(raw any) string {
	switch value := raw.(type) {
	case nil:
		return ""
	case string:
		return strings.TrimSpace(value)
	case float64:
		if value == float64(int64(value)) {
			return strconv.FormatInt(int64(value), 10)
		}
		return strconv.FormatFloat(value, 'f', -1, 64)
	case json.Number:
		return value.String()
	case bool:
		if value {
			return "true"
		}
		return "false"
	default:
		return strings.TrimSpace(fmt.Sprint(raw))
	}
}

func includedRequestRows(body map[string]any) []map[string]any {
	rawRows, ok := body["included_studies"].([]any)
	if !ok {
		return nil
	}
	rows := make([]map[string]any, 0, len(rawRows))
	for _, raw := range rawRows {
		row, ok := raw.(map[string]any)
		if ok {
			rows = append(rows, row)
		}
	}
	return rows
}

func includedIDsFromBody(body map[string]any) []string {
	rawIDs, ok := body["included_study_ids"].([]any)
	if !ok {
		return nil
	}
	ids := make([]string, 0, len(rawIDs))
	for _, raw := range rawIDs {
		ids = append(ids, stringValue(raw))
	}
	return ids
}

func referencesFromBody(body map[string]any) []map[string]any {
	rawRefs, ok := body["references"].([]any)
	if !ok {
		return nil
	}
	refs := make([]map[string]any, 0, len(rawRefs))
	for _, raw := range rawRefs {
		entry, ok := raw.(map[string]any)
		if ok {
			refs = append(refs, entry)
		}
	}
	return refs
}

func sameStringSet(values []string, target map[string]struct{}) bool {
	if len(values) != len(target) {
		return false
	}
	seen := make(map[string]struct{}, len(values))
	for _, value := range values {
		if _, ok := target[value]; !ok {
			return false
		}
		if _, duplicate := seen[value]; duplicate {
			return false
		}
		seen[value] = struct{}{}
	}
	return len(seen) == len(target)
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}

func validateIncluded(rows []map[string]any) map[string]any {
	submittedIDs := make([]string, 0, len(rows))
	isValid := len(rows) == len(servicePayload.IncludedRows)

	for _, row := range rows {
		studyID := stringValue(row["study_id"])
		submittedIDs = append(submittedIDs, studyID)
		target, ok := includedByID[studyID]
		if !ok {
			isValid = false
			continue
		}
		if stringValue(row["short_citation"]) != target.ShortCitation {
			isValid = false
		}
		if stringValue(row["study_design"]) != target.StudyDesign {
			isValid = false
		}
		if stringValue(row["population_scope"]) != target.PopulationScope {
			isValid = false
		}
		if stringValue(row["duration_weeks"]) != target.DurationWeeks {
			isValid = false
		}
		if stringValue(row["comparator_type"]) != target.ComparatorType {
			isValid = false
		}
		if stringValue(row["primary_outcome_direction"]) != target.PrimaryOutcomeDirection {
			isValid = false
		}
	}

	if !sameStringSet(submittedIDs, eligibleSet) {
		isValid = false
	}

	return map[string]any{
		"is_valid":        isValid,
		"snapshot_id":     servicePayload.SnapshotID,
		"submitted_count": len(rows),
	}
}

func entryMatches(entry map[string]any, target referenceTarget) bool {
	doi := normalizeDOI(stringValue(entry["doi"]))
	title := normalizeText(stringValue(entry["title"]))
	journal := normalizeText(firstNonEmpty(stringValue(entry["journal"]), stringValue(entry["journaltitle"])))
	year := stringValue(entry["year"])
	author := normalizeText(firstNonEmpty(stringValue(entry["author"]), stringValue(entry["authors"])))

	targetDOI := normalizeDOI(target.DOI)
	targetTitle := normalizeText(target.Title)
	targetJournal := normalizeText(target.Journal)
	targetYear := strings.TrimSpace(target.Year)

	if doi != "" && doi == targetDOI {
		return true
	}
	if title == targetTitle && journal == targetJournal && year == targetYear {
		return true
	}
	return strings.Contains(author, normalizeText(target.FirstAuthorLastName)) && title == targetTitle
}

func validateReferences(entries []map[string]any, includedIDs []string) map[string]any {
	matched := make(map[string]struct{}, len(servicePayload.ReferenceTargets))
	for _, studyID := range includedIDs {
		target, ok := servicePayload.ReferenceTargets[studyID]
		if !ok {
			continue
		}
		for _, entry := range entries {
			if entryMatches(entry, target) {
				matched[studyID] = struct{}{}
				break
			}
		}
	}

	submittedDOIs := make([]string, 0, len(entries))
	for _, entry := range entries {
		doi := normalizeDOI(stringValue(entry["doi"]))
		if doi != "" {
			submittedDOIs = append(submittedDOIs, doi)
		}
	}

	uniqueDOIs := len(submittedDOIs) == len(makeSet(submittedDOIs))
	isValid := sameStringSet(includedIDs, eligibleSet) &&
		len(matched) == len(eligibleSet) &&
		uniqueDOIs &&
		len(entries) == len(servicePayload.ReferenceTargets)

	return map[string]any{
		"is_valid":                  isValid,
		"matched_reference_count":   len(matched),
		"snapshot_id":               servicePayload.SnapshotID,
		"submitted_reference_count": len(entries),
	}
}

func containsAny(text string, terms []string) bool {
	for _, term := range terms {
		if strings.Contains(text, term) {
			return true
		}
	}
	return false
}

func validateSummary(summary string, includedIDs []string) map[string]any {
	text := normalizeText(summary)
	benefitTerms := []string{"benefit", "improved", "improves", "improvement", "reduce", "reduced", "decrease", "decreased"}
	passiveTerms := []string{"passive", "usual care", "control"}
	activeTerms := []string{"active", "dietetic", "mediterranean", "conventional dieting"}
	similarTerms := []string{"similar", "non inferior", "noninferior", "comparable", "not superior", "no consistent superiority", "no additional metabolic benefit"}
	cautionTerms := []string{"small", "modest", "limited", "cautious"}
	bannedTerms := []string{"superior to active", "clearly superior to active", "consistently superior to active", "best dietary approach", "proves superiority over active"}

	scopeOK := (strings.Contains(text, "adult") || strings.Contains(text, "adults")) &&
		(strings.Contains(text, "type 2 diabetes") || strings.Contains(text, "t2d"))
	passiveOK := containsAny(text, passiveTerms) && containsAny(text, benefitTerms)
	activeOK := containsAny(text, activeTerms) && containsAny(text, similarTerms)
	cautionOK := containsAny(text, cautionTerms)
	bannedFound := containsAny(text, bannedTerms)

	isValid := sameStringSet(includedIDs, eligibleSet) &&
		len(strings.Fields(summary)) >= 40 &&
		scopeOK &&
		passiveOK &&
		activeOK &&
		cautionOK &&
		!bannedFound

	return map[string]any{
		"is_valid":    isValid,
		"snapshot_id": servicePayload.SnapshotID,
	}
}

func writeJSON(w http.ResponseWriter, status int, payload map[string]any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

type handler struct{}

func (handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	switch {
	case r.Method == http.MethodGet && r.URL.Path == "/health":
		writeJSON(w, http.StatusOK, map[string]any{
			"snapshot_id": servicePayload.SnapshotID,
			"status":      "ok",
		})
		return
	case r.Method == http.MethodPost && r.URL.Path == "/validate/included-studies":
		var body map[string]any
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid_json"})
			return
		}
		writeJSON(w, http.StatusOK, validateIncluded(includedRequestRows(body)))
		return
	case r.Method == http.MethodPost && r.URL.Path == "/validate/references":
		var body map[string]any
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid_json"})
			return
		}
		writeJSON(w, http.StatusOK, validateReferences(referencesFromBody(body), includedIDsFromBody(body)))
		return
	case r.Method == http.MethodPost && r.URL.Path == "/validate/summary":
		var body map[string]any
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid_json"})
			return
		}
		writeJSON(w, http.StatusOK, validateSummary(stringValue(body["summary"]), includedIDsFromBody(body)))
		return
	default:
		http.NotFound(w, r)
	}
}

func main() {
	server := &http.Server{
		Addr:    "127.0.0.1:8123",
		Handler: handler{},
	}
	log.Fatal(server.ListenAndServe())
}
