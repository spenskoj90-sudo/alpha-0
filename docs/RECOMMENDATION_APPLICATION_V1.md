# Recommendation Application v1

Application composition around the existing RecommendationService. It preserves provider/model identity, confidence and provenance and introduces no authorization, persistence, network I/O or action execution. The existing API authorization boundary remains authoritative; this is not a claim that `/v1/recommendations` is wired to it.
