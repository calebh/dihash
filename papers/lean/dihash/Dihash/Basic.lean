/-
  Transitivity of a min-based ordering on finite sets of natural numbers.

  Given finite sets A, B, C ⊆ ℕ with all pairwise set differences nonempty,
  define A < B iff min(A \ B) < min(B \ A).
  We prove: if A < B and B < C then A < C.
-/

import Mathlib.Data.Finset.Lattice.Basic

open Finset

/-- The ordering relation: A < B iff min(A \ B) <ℕ min(B \ A). -/
def fset_lt (A B : Finset ℕ) (hAB : (A \ B).Nonempty) (hBA : (B \ A).Nonempty) : Prop :=
  (A \ B).min' hAB < (B \ A).min' hBA

/-- Key observation: if x ∈ S and x < min(S \ T), then x ∈ T.
    Proof: if x ∉ T then x ∈ S \ T, contradicting x < min(S \ T). -/
lemma mem_of_mem_of_lt_min'_sdiff
    {S T : Finset ℕ} (hST : (S \ T).Nonempty)
    {x : ℕ} (hxS : x ∈ S) (hlt : x < (S \ T).min' hST) : x ∈ T := by
  by_contra hxT
  have hx_mem : x ∈ S \ T := mem_sdiff.mpr ⟨hxS, hxT⟩
  have := min'_le _ x hx_mem
  omega

/-- Transitivity: if A < B and B < C then A < C. -/
theorem fset_lt_trans {A B C : Finset ℕ}
    (hAB : (A \ B).Nonempty) (hBA : (B \ A).Nonempty)
    (hBC : (B \ C).Nonempty) (hCB : (C \ B).Nonempty)
    (hAC : (A \ C).Nonempty) (hCA : (C \ A).Nonempty)
    (hab : fset_lt A B hAB hBA) (hbc : fset_lt B C hBC hCB) :
    fset_lt A C hAC hCA := by
  unfold fset_lt at *
  -- Name the six key values
  set a := (A \ B).min' hAB with ha_def
  set b := (B \ A).min' hBA with hb_def
  set β := (B \ C).min' hBC with hβ_def
  set γ := (C \ B).min' hCB with hγ_def
  set α := (A \ C).min' hAC with hα_def
  set δ := (C \ A).min' hCA with hδ_def
  -- Hypotheses: a < b and β < γ. Goal: α < δ.
  -- Extract membership from the min' witnesses
  have ha_mem := min'_mem (A \ B) hAB   -- a ∈ A \ B
  have hβ_mem := min'_mem (B \ C) hBC   -- β ∈ B \ C
  have hδ_mem := min'_mem (C \ A) hCA   -- δ ∈ C \ A
  -- Decompose set-difference membership
  have ha_A  : a ∈ A := (mem_sdiff.mp ha_mem).1
  have ha_nB : a ∉ B := (mem_sdiff.mp ha_mem).2
  have hβ_B  : β ∈ B := (mem_sdiff.mp hβ_mem).1
  have hβ_nC : β ∉ C := (mem_sdiff.mp hβ_mem).2
  have hδ_C  : δ ∈ C := (mem_sdiff.mp hδ_mem).1
  have hδ_nA : δ ∉ A := (mem_sdiff.mp hδ_mem).2
  /-
    The proof splits on whether δ ∈ B, then on further membership questions.
    In every branch we build a chain of inequalities showing α < δ
    (or reach a contradiction).
  -/
  by_cases hδ_B : δ ∈ B
  · /-
      Case 2: δ ∈ B.
      Then δ ∈ B \ A, so b ≤ δ.
    -/
    have hδ_BA : δ ∈ B \ A := mem_sdiff.mpr ⟨hδ_B, hδ_nA⟩
    have hb_le_δ : b ≤ δ := min'_le (B \ A) δ hδ_BA
    by_cases ha_C : a ∈ C
    · /-
        Sub-case 2b: a ∈ C.
        Then a ∈ C \ B (since a ∉ B), so γ ≤ a.
        Therefore β < γ ≤ a < b, hence β < b.
        Since β ∈ B and β < b = min(B \ A), observation (O1) gives β ∈ A.
        Then β ∈ A \ C, so α ≤ β.
        Chain: α ≤ β < γ ≤ a < b ≤ δ, hence α < δ. ✓
      -/
      have ha_CB : a ∈ C \ B := mem_sdiff.mpr ⟨ha_C, ha_nB⟩
      have hγ_le_a : γ ≤ a := min'_le (C \ B) a ha_CB
      have hβ_lt_b : β < b := by omega
      have hβ_A : β ∈ A :=
        mem_of_mem_of_lt_min'_sdiff hBA hβ_B hβ_lt_b
      have hβ_AC : β ∈ A \ C := mem_sdiff.mpr ⟨hβ_A, hβ_nC⟩
      have hα_le_β : α ≤ β := min'_le (A \ C) β hβ_AC
      omega
    · /-
        Sub-case 2a: a ∉ C.
        Then a ∈ A \ C, so α ≤ a.
        Chain: α ≤ a < b ≤ δ, hence α < δ. ✓
      -/
      have ha_AC : a ∈ A \ C := mem_sdiff.mpr ⟨ha_A, ha_C⟩
      have hα_le_a : α ≤ a := min'_le (A \ C) a ha_AC
      omega
  · /-
      Case 1: δ ∉ B.
      Then δ ∈ C \ B (since δ ∈ C), so γ ≤ δ.
    -/
    have hδ_CB : δ ∈ C \ B := mem_sdiff.mpr ⟨hδ_C, hδ_B⟩
    have hγ_le_δ : γ ≤ δ := min'_le (C \ B) δ hδ_CB
    by_cases hβ_A : β ∈ A
    · /-
        Sub-case 1a: β ∈ A.
        Then β ∈ A \ C, so α ≤ β.
        Chain: α ≤ β < γ ≤ δ, hence α < δ. ✓
      -/
      have hβ_AC : β ∈ A \ C := mem_sdiff.mpr ⟨hβ_A, hβ_nC⟩
      have hα_le_β : α ≤ β := min'_le (A \ C) β hβ_AC
      omega
    · /-
        Sub-case 1b: β ∉ A.
        Then β ∈ B \ A (since β ∈ B), so b ≤ β.
      -/
      have hβ_BA : β ∈ B \ A := mem_sdiff.mpr ⟨hβ_B, hβ_A⟩
      have hb_le_β : b ≤ β := min'_le (B \ A) β hβ_BA
      by_cases ha_C : a ∈ C
      · /-
          Sub-sub-case: a ∈ C.
          Then a ∈ C \ B, so γ ≤ a.
          Chain: γ ≤ a < b ≤ β < γ — contradiction. ✓
        -/
        have ha_CB : a ∈ C \ B := mem_sdiff.mpr ⟨ha_C, ha_nB⟩
        have hγ_le_a : γ ≤ a := min'_le (C \ B) a ha_CB
        omega
      · /-
          Sub-sub-case: a ∉ C.
          Then a ∈ A \ C, so α ≤ a.
          Chain: α ≤ a < b ≤ β < γ ≤ δ, hence α < δ. ✓
        -/
        have ha_AC : a ∈ A \ C := mem_sdiff.mpr ⟨ha_A, ha_C⟩
        have hα_le_a : α ≤ a := min'_le (A \ C) a ha_AC
        omega
