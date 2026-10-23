Inductive Node : Set :=
  Nd : nat -> Node.
Inductive Label : Set :=
  Lbl : nat -> Label.

(*
Inductive TableDistinguishStrong : Node -> Node -> Prop :=
  TDStrong : False -> forall (p : Node) (q : Node), TableDistinguishStrong p q.

Inductive TableDistinguishWeak : Node -> Node -> list Label -> Prop :=
  TDWeak : False -> forall (p : Node) (q : Node) (path : list Label), TableDistinguishWeak p q path.

Inductive Language : Node -> Node -> list Label -> Prop :=
  Lang : False -> forall (p : Node) (q : Node) (path : list Label), Language p q path.

*)

Axiom TableDistinguishStrong : Node -> Node -> Prop.
Axiom TableDistinguishWeak : Node -> Node -> nat -> Prop.
Axiom Language : Node -> Node -> list Label -> Prop.

Theorem lemma1 :
  forall (p : Node) (q : Node) (w : list Label), Language p q w -> TableDistinguishStrong p q.
Proof.
Admitted.

Theorem lemma2 :
  forall (n : nat) (p : Node) (q : Node), TableDistinguishWeak p q n -> exists w', Language p q w'.
Proof.
Admitted.

Theorem lemma3 :
  forall (p : Node) (q : Node), TableDistinguishStrong p q -> exists (n : nat), TableDistinguishWeak p q n.
Admitted.

Theorem theorem1 :
  forall (p : Node) (q : Node), TableDistinguishStrong p q <-> exists (w : list Label), Language p q w.
Proof.
  intros.
  constructor.
  - intros.
    pose proof (lemma3 p q H).
    destruct H0.
    eapply lemma2.
    eauto.
  - intros.
    destruct H.
    eapply lemma1.
    eauto.
Qed.
