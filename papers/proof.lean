theorem table_correct (F : List nat -> nat -> nat -> Prop) (G : nat -> nat -> Prop) :
    forall (w : List nat) (p : nat) (q : nat), F w p q -> G p q :=
    by
      intro w
      induction w
      sorry
      intros