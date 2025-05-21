theorem lemma1 (lang : List nat -> nat -> nat -> Prop) (tableStrong : nat -> nat -> Prop) :
    forall (w : List nat) (p : nat) (q : nat), lang w p q -> tableStrong p q :=
    by
      sorry

theorem lemma2 (lang : List nat -> nat -> nat -> Prop) (tableWeak : List nat -> nat -> nat -> Prop) :
    forall (w : List nat) (p : nat) (q : nat), tableWeak w p q -> lang w p q :=
    by
      sorry

theorem lemma3 (tableStrong : nat -> nat -> Prop) (tableWeak : List nat -> nat -> nat -> Prop) :
    forall (p : nat) (q : nat), tableStrong p q -> exists (w : List nat), tableWeak w p q :=
    by
      sorry

theorem theorem1 (lang : List nat -> nat -> nat -> Prop) (tableStrong : nat -> nat -> Prop) :
    forall (p : nat) (q : nat), tableStrong p q <-> exists (w : List nat), lang w p q :=
    by
      


theorem table_correct2 (F : List nat -> nat -> nat -> Prop) (G : nat -> nat -> Prop) :
    forall (p : nat) (q : nat), G p q -> exists (w : List nat), F w p q :=
    by
      intros


theorem table_correct (F : List nat -> nat -> nat -> Prop) (G : nat -> nat -> Prop) :
    forall (w : List nat) (p : nat) (q : nat), F w p q -> G p q :=
    by
      intro w
      induction w
      sorry
      intros