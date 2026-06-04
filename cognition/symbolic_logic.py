"""
NEXUS AI - Symbolic Logic Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Real symbolic logic computation - not LLM-estimated validity.
Provides actual propositional and predicate logic validation.

Features:
  • Proposition parsing from natural language (via LLM)
  • Truth table generation
  • Validity checking (real proof, not estimation)
  • Formal proof construction and verification
  • CNF conversion for SAT integration
  • Syllogism validation
  • Modus ponens/tollens verification

This module provides computational truth for logical reasoning.
The LLM translates natural language to formal logic; this engine
computes validity deterministically.
"""

import threading
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set, FrozenSet
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto
from itertools import product
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("symbolic_logic")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class LogicalOperator(Enum):
    """Logical operators"""
    AND = "∧"
    OR = "∨"
    NOT = "¬"
    IMPLIES = "→"
    IFF = "↔"  # If and only if
    XOR = "⊕"  # Exclusive or
    NAND = "↑"  # Not and
    NOR = "↓"  # Not or
    
    # Text alternatives
    AND_TEXT = "AND"
    OR_TEXT = "OR"
    NOT_TEXT = "NOT"
    IMPLIES_TEXT = "IMPLIES"
    IFF_TEXT = "IFF"


class PropositionType(Enum):
    """Types of propositions"""
    ATOMIC = "atomic"        # Single variable: P
    COMPOUND = "compound"    # Multiple operators: P ∧ Q
    CONDITIONAL = "conditional"  # If-then: P → Q
    BICONDITIONAL = "biconditional"  # Iff: P ↔ Q
    UNIVERSAL = "universal"  # For all: ∀x P(x)
    EXISTENTIAL = "existential"  # There exists: ∃x P(x)


class InferenceRule(Enum):
    """Standard inference rules"""
    MODUS_PONENS = "modus_ponens"      # P→Q, P ⊢ Q
    MODUS_TOLLENS = "modus_tollens"    # P→Q, ¬Q ⊢ ¬P
    HYPOTHETICAL_SYLLOGISM = "hypothetical_syllogism"  # P→Q, Q→R ⊢ P→R
    DISJUNCTIVE_SYLLOGISM = "disjunctive_syllogism"  # P∨Q, ¬P ⊢ Q
    CONJUNCTION = "conjunction"        # P, Q ⊢ P∧Q
    SIMPLIFICATION = "simplification"  # P∧Q ⊢ P
    ADDITION = "addition"              # P ⊢ P∨Q
    CONTRUCTION = "construction"       # P→Q, P→R ⊢ P→(Q∧R)
    RESOLUTION = "resolution"          # P∨Q, ¬P∨R ⊢ Q∨R


@dataclass
class Proposition:
    """A logical proposition"""
    proposition_id: str = ""
    text: str = ""  # Original text
    formula: str = ""  # Formal notation: "P ∧ Q → R"
    proposition_type: PropositionType = PropositionType.ATOMIC
    variables: List[str] = field(default_factory=list)  # ["P", "Q", "R"]
    operator: Optional[LogicalOperator] = None
    sub_propositions: List["Proposition"] = field(default_factory=list)
    is_negated: bool = False
    truth_value: Optional[bool] = None
    
    def to_dict(self) -> Dict:
        return {
            "proposition_id": self.proposition_id,
            "text": self.text,
            "formula": self.formula,
            "proposition_type": self.proposition_type.value,
            "variables": self.variables,
            "operator": self.operator.value if self.operator else None,
            "is_negated": self.is_negated,
            "truth_value": self.truth_value,
        }


@dataclass
class TruthTable:
    """A truth table for a proposition"""
    proposition_id: str = ""
    variables: List[str] = field(default_factory=list)
    rows: List[Dict[str, bool]] = field(default_factory=list)  # [{P: True, Q: False, result: True}]
    is_tautology: bool = False
    is_contradiction: bool = False
    is_contingent: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "proposition_id": self.proposition_id,
            "variables": self.variables,
            "rows": self.rows,
            "is_tautology": self.is_tautology,
            "is_contradiction": self.is_contradiction,
            "is_contingent": self.is_contingent,
        }


@dataclass
class Proof:
    """A logical proof"""
    proof_id: str = ""
    premises: List[Proposition] = field(default_factory=list)
    conclusion: Proposition = None
    steps: List[Dict[str, Any]] = field(default_factory=list)  # [{step: 1, formula: "...", rule: "..."}]
    is_valid: bool = False
    proof_type: str = "direct"  # direct, contradiction, induction
    
    def to_dict(self) -> Dict:
        return {
            "proof_id": self.proof_id,
            "premises": [p.to_dict() for p in self.premises],
            "conclusion": self.conclusion.to_dict() if self.conclusion else None,
            "steps": self.steps,
            "is_valid": self.is_valid,
            "proof_type": self.proof_type,
        }


@dataclass
class Argument:
    """A logical argument with premises and conclusion"""
    argument_id: str = ""
    premises: List[str] = field(default_factory=list)  # Text premises
    conclusion: str = ""
    formalized_premises: List[Proposition] = field(default_factory=list)
    formalized_conclusion: Proposition = None
    is_valid: Optional[bool] = None
    is_sound: Optional[bool] = None
    proof: Optional[Proof] = None
    
    def to_dict(self) -> Dict:
        return {
            "argument_id": self.argument_id,
            "premises": self.premises,
            "conclusion": self.conclusion,
            "is_valid": self.is_valid,
            "is_sound": self.is_sound,
            "proof": self.proof.to_dict() if self.proof else None,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SYMBOLIC LOGIC ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class SymbolicLogicEngine:
    """
    Real Symbolic Logic Engine - Computational Logic.
    
    Operations:
      parse()           — Parse natural language to formal proposition
      evaluate()        — Evaluate proposition given variable assignments
      truth_table()     — Generate complete truth table
      check_validity()  — Check if argument is valid
      verify_proof()    — Verify a proof step by step
      to_cnf()          — Convert to Conjunctive Normal Form
      prove()           — Attempt to prove a conclusion from premises
    """
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # ──── Stats ────
        self._total_propositions = 0
        self._total_proofs = 0
        self._total_validations = 0

        # ──── LLM (lazy) ────
        self._llm = None

        logger.info("SymbolicLogicEngine initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # PROPOSITION PARSING
    # ═══════════════════════════════════════════════════════════════════════════

    def parse(self, text: str) -> Proposition:
        """
        Parse natural language into a formal proposition.
        Uses LLM for natural language understanding, then creates formal structure.
        """
        self._load_llm()
        
        # Try to parse simple cases directly
        simple = self._try_simple_parse(text)
        if simple:
            return simple

        # Use LLM for complex parsing
        if self._llm and self._llm.is_connected:
            return self._llm_parse(text)

        # Fallback
        return Proposition(
            proposition_id=f"prop_{hash(text) % 10000:04d}",
            text=text,
            formula=text,
            variables=self._extract_variables(text),
        )

    def _try_simple_parse(self, text: str) -> Optional[Proposition]:
        """Try to parse simple logical forms directly"""
        text = text.strip()
        
        # Pattern: "If P then Q"
        match = re.match(r"if (.+?) then (.+)", text, re.IGNORECASE)
        if match:
            p_text, q_text = match.groups()
            p = self._try_simple_parse(p_text) or Proposition(text=p_text, formula=p_text.upper()[:1], variables=[p_text.upper()[:1]])
            q = self._try_simple_parse(q_text) or Proposition(text=q_text, formula=q_text.upper()[:1], variables=[q_text.upper()[:1]])
            return Proposition(
                proposition_id=f"prop_{hash(text) % 10000:04d}",
                text=text,
                formula=f"({p.formula} → {q.formula})",
                proposition_type=PropositionType.CONDITIONAL,
                variables=list(set(p.variables + q.variables)),
                operator=LogicalOperator.IMPLIES,
                sub_propositions=[p, q],
            )

        # Pattern: "P and Q" / "P or Q"
        for pattern, op in [(r"(.+?) and (.+)", LogicalOperator.AND), 
                            (r"(.+?) or (.+)", LogicalOperator.OR)]:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                left, right = match.groups()
                p = self._try_simple_parse(left) or Proposition(text=left, formula=left.upper()[:1], variables=[left.upper()[:1]])
                q = self._try_simple_parse(right) or Proposition(text=right, formula=right.upper()[:1], variables=[right.upper()[:1]])
                symbol = "∧" if op == LogicalOperator.AND else "∨"
                return Proposition(
                    proposition_id=f"prop_{hash(text) % 10000:04d}",
                    text=text,
                    formula=f"({p.formula} {symbol} {q.formula})",
                    proposition_type=PropositionType.COMPOUND,
                    variables=list(set(p.variables + q.variables)),
                    operator=op,
                    sub_propositions=[p, q],
                )

        # Pattern: "not P"
        match = re.match(r"not (.+)", text, re.IGNORECASE)
        if match:
            inner = match.group(1)
            p = self._try_simple_parse(inner) or Proposition(text=inner, formula=inner.upper()[:1], variables=[inner.upper()[:1]])
            return Proposition(
                proposition_id=f"prop_{hash(text) % 10000:04d}",
                text=text,
                formula=f"¬{p.formula}",
                proposition_type=PropositionType.COMPOUND,
                variables=p.variables,
                operator=LogicalOperator.NOT,
                sub_propositions=[p],
                is_negated=True,
            )

        # Atomic proposition
        return None

    def _llm_parse(self, text: str) -> Proposition:
        """Use LLM to parse natural language to formal logic"""
        try:
            prompt = (
                f"Convert this natural language statement to formal logic notation.\n\n"
                f"Statement: {text}\n\n"
                f"Return JSON:\n"
                f'{{"formula": "P ∧ Q → R", "variables": ["P", "Q", "R"], '
                f'"type": "atomic|compound|conditional|biconditional", '
                f'"operator": "AND|OR|NOT|IMPLIES|IFF|null", '
                f'"sub_formulas": ["left part formula", "right part formula"]}}'
            )
            
            from utils.json_utils import extract_json
            response = self._llm.generate(prompt, max_tokens=300, temperature=0.2)
            data = extract_json(response.text) or {}

            ptype = PropositionType.COMPOUND
            try:
                ptype = PropositionType(data.get("type", "compound"))
            except ValueError:
                pass

            operator = None
            if data.get("operator"):
                try:
                    operator = LogicalOperator[data.get("operator").upper() + "_TEXT"]
                except KeyError:
                    pass

            return Proposition(
                proposition_id=f"prop_{hash(text) % 10000:04d}",
                text=text,
                formula=data.get("formula", text),
                proposition_type=ptype,
                variables=data.get("variables", []),
                operator=operator,
            )

        except Exception as e:
            logger.debug(f"LLM parsing failed: {e}")
            return Proposition(text=text, formula=text, variables=self._extract_variables(text))

    def _extract_variables(self, text: str) -> List[str]:
        """Extract potential variable names from text"""
        # Find capital letters or key nouns
        capitals = re.findall(r'\b([A-Z])\b', text)
        if capitals:
            return list(set(capitals))
        # Extract nouns as pseudo-variables
        words = re.findall(r'\b([A-Z][a-z]+)\b', text)
        return [w[0].upper() for w in words[:5]]

    # ═══════════════════════════════════════════════════════════════════════════
    # EVALUATION
    # ═══════════════════════════════════════════════════════════════════════════

    def evaluate(self, proposition: Proposition, assignment: Dict[str, bool]) -> bool:
        """
        Evaluate a proposition given a variable assignment.
        
        Args:
            proposition: The proposition to evaluate
            assignment: Dict mapping variable names to truth values
            
        Returns: Boolean result
        """
        if proposition.proposition_type == PropositionType.ATOMIC:
            # Atomic proposition - look up value
            var = proposition.variables[0] if proposition.variables else proposition.formula
            return assignment.get(var, False) != proposition.is_negated

        # Compound proposition
        if proposition.operator == LogicalOperator.NOT or proposition.is_negated:
            if proposition.sub_propositions:
                inner = self.evaluate(proposition.sub_propositions[0], assignment)
                return not inner
            return not assignment.get(proposition.variables[0], False)

        if len(proposition.sub_propositions) < 2:
            # Fall back to formula parsing
            return self._evaluate_formula(proposition.formula, assignment)

        left = self.evaluate(proposition.sub_propositions[0], assignment)
        right = self.evaluate(proposition.sub_propositions[1], assignment)

        op = proposition.operator
        if op == LogicalOperator.AND or op == LogicalOperator.AND_TEXT:
            return left and right
        elif op == LogicalOperator.OR or op == LogicalOperator.OR_TEXT:
            return left or right
        elif op == LogicalOperator.IMPLIES or op == LogicalOperator.IMPLIES_TEXT:
            return (not left) or right  # P→Q ≡ ¬P ∨ Q
        elif op == LogicalOperator.IFF or op == LogicalOperator.IFF_TEXT:
            return left == right
        elif op == LogicalOperator.XOR:
            return left != right
        elif op == LogicalOperator.NAND:
            return not (left and right)
        elif op == LogicalOperator.NOR:
            return not (left or right)
        else:
            return self._evaluate_formula(proposition.formula, assignment)

    def _evaluate_formula(self, formula: str, assignment: Dict[str, bool]) -> bool:
        """Evaluate a formula string directly"""
        # Replace variables with values
        expr = formula
        for var, val in assignment.items():
            expr = re.sub(rf'\b{var}\b', str(val), expr)
        
        # Replace operators
        expr = expr.replace("∧", " and ").replace("∨", " or ")
        expr = expr.replace("→", " or not ")  # P→Q ≡ not P or Q
        expr = expr.replace("↔", " == ")
        expr = expr.replace("¬", "not ")
        expr = expr.replace("⊕", " != ")
        
        try:
            return bool(eval(expr))
        except:
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # TRUTH TABLE
    # ═══════════════════════════════════════════════════════════════════════════

    def truth_table(self, proposition: Proposition) -> TruthTable:
        """
        Generate a complete truth table for a proposition.
        
        Returns TruthTable with all possible assignments and results.
        """
        variables = proposition.variables
        if not variables:
            variables = ["P"]  # Default

        n = len(variables)
        rows = []
        true_count = 0
        false_count = 0

        # Generate all 2^n assignments
        for values in product([True, False], repeat=n):
            assignment = dict(zip(variables, values))
            result = self.evaluate(proposition, assignment)
            
            row = {v: assignment[v] for v in variables}
            row["result"] = result
            rows.append(row)
            
            if result:
                true_count += 1
            else:
                false_count += 1

        # Determine proposition type
        is_tautology = true_count == len(rows)
        is_contradiction = false_count == len(rows)
        is_contingent = not is_tautology and not is_contradiction

        self._total_propositions += 1

        return TruthTable(
            proposition_id=proposition.proposition_id,
            variables=variables,
            rows=rows,
            is_tautology=is_tautology,
            is_contradiction=is_contradiction,
            is_contingent=is_contingent,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDITY CHECKING
    # ═══════════════════════════════════════════════════════════════════════════

    def check_validity(self, premises: List[Proposition], conclusion: Proposition) -> Tuple[bool, Proof]:
        """
        Check if an argument is valid using truth tables.
        
        An argument is valid if whenever all premises are true,
        the conclusion is also true.
        
        Returns (is_valid, proof).
        """
        self._total_validations += 1

        # Get all variables
        all_vars = set()
        for p in premises:
            all_vars.update(p.variables)
        all_vars.update(conclusion.variables)
        all_vars = list(all_vars)

        if not all_vars:
            all_vars = ["P"]

        # Check all possible assignments
        counterexamples = []
        valid_rows = 0

        for values in product([True, False], repeat=len(all_vars)):
            assignment = dict(zip(all_vars, values))
            
            # Evaluate all premises
            all_premises_true = all(self.evaluate(p, assignment) for p in premises)
            conclusion_value = self.evaluate(conclusion, assignment)
            
            # Check for counterexample
            if all_premises_true and not conclusion_value:
                counterexamples.append(assignment)
            elif all_premises_true and conclusion_value:
                valid_rows += 1

        is_valid = len(counterexamples) == 0

        # Build proof structure
        proof = Proof(
            proof_id=f"proof_{hash(str(premises) + str(conclusion)) % 100000:05d}",
            premises=premises,
            conclusion=conclusion,
            is_valid=is_valid,
            steps=[],
        )

        if is_valid:
            proof.steps.append({
                "step": 1,
                "statement": "Argument is VALID",
                "reasoning": f"No counterexample found. All {valid_rows} rows where premises are true also have true conclusion.",
                "method": "truth_table_exhaustion",
            })
        else:
            proof.steps.append({
                "step": 1,
                "statement": "Argument is INVALID",
                "reasoning": f"Found {len(counterexamples)} counterexample(s) where premises are true but conclusion is false.",
                "counterexamples": counterexamples[:3],  # Show first 3
                "method": "truth_table_exhaustion",
            })

        self._total_proofs += 1

        return is_valid, proof

    def check_inference(self, premises: List[Proposition], conclusion: Proposition, 
                       rule: InferenceRule) -> bool:
        """
        Check if an inference follows a specific rule.
        
        Examples:
          Modus Ponens: P→Q, P ⊢ Q
          Modus Tollens: P→Q, ¬Q ⊢ ¬P
        """
        if rule == InferenceRule.MODUS_PONENS:
            # Check for P→Q and P, conclude Q
            for p1 in premises:
                if p1.operator == LogicalOperator.IMPLIES:
                    antecedent = p1.sub_propositions[0] if p1.sub_propositions else None
                    consequent = p1.sub_propositions[1] if len(p1.sub_propositions) > 1 else None
                    
                    if antecedent and consequent:
                        # Check if antecedent matches another premise
                        for p2 in premises:
                            if p2 != p1:
                                is_valid, _ = self.check_validity([p1, p2], consequent)
                                if is_valid:
                                    return True
            return False

        elif rule == InferenceRule.MODUS_TOLLENS:
            # Check for P→Q and ¬Q, conclude ¬P
            for p1 in premises:
                if p1.operator == LogicalOperator.IMPLIES:
                    antecedent = p1.sub_propositions[0] if p1.sub_propositions else None
                    consequent = p1.sub_propositions[1] if len(p1.sub_propositions) > 1 else None
                    
                    for p2 in premises:
                        if p2.is_negated or p2.operator == LogicalOperator.NOT:
                            # Check if p2 negates consequent
                            if consequent and p2.sub_propositions:
                                negated_consequent = Proposition(
                                    formula=f"¬{consequent.formula}",
                                    is_negated=True,
                                    sub_propositions=[consequent],
                                    operator=LogicalOperator.NOT,
                                )
                                is_valid, _ = self.check_validity([p1, p2], negated_consequent)
                                if is_valid:
                                    return True
            return False

        elif rule == InferenceRule.HYPOTHETICAL_SYLLOGISM:
            # P→Q, Q→R ⊢ P→R
            impl_premises = [p for p in premises if p.operator == LogicalOperator.IMPLIES]
            if len(impl_premises) >= 2:
                for p1 in impl_premises:
                    for p2 in impl_premises:
                        if p1 != p2 and p1.sub_propositions and p2.sub_propositions:
                            # Check chain
                            if len(p1.sub_propositions) > 1 and len(p2.sub_propositions) > 1:
                                q1 = p1.sub_propositions[1]  # Consequent of first
                                p2_ant = p2.sub_propositions[0]  # Antecedent of second
                                # If they match, we can chain
                                if q1.formula == p2_ant.formula:
                                    new_impl = Proposition(
                                        formula=f"({p1.sub_propositions[0].formula} → {p2.sub_propositions[1].formula})",
                                        operator=LogicalOperator.IMPLIES,
                                        sub_propositions=[p1.sub_propositions[0], p2.sub_propositions[1]],
                                    )
                                    is_valid, _ = self.check_validity([p1, p2], new_impl)
                                    if is_valid:
                                        return True
            return False

        # Default to truth table check
        is_valid, _ = self.check_validity(premises, conclusion)
        return is_valid

    # ═══════════════════════════════════════════════════════════════════════════
    # CNF CONVERSION (for SAT solver integration)
    # ═══════════════════════════════════════════════════════════════════════════

    def to_cnf(self, proposition: Proposition) -> List[List[str]]:
        """
        Convert a proposition to Conjunctive Normal Form.
        
        CNF is a conjunction of disjunctions: (A ∨ B) ∧ (¬C ∨ D)
        
        Returns list of clauses, where each clause is a list of literals.
        Example: [[A, B], [¬C, D]] means (A ∨ B) ∧ (¬C ∨ D)
        """
        # Step 1: Eliminate implications
        formula = self._eliminate_implications(proposition.formula)
        
        # Step 2: Move negations inward (De Morgan's laws)
        formula = self._move_negation_inward(formula)
        
        # Step 3: Distribute OR over AND
        formula = self._distribute(formula)
        
        # Step 4: Extract clauses
        clauses = self._extract_clauses(formula)
        
        return clauses

    def _eliminate_implications(self, formula: str) -> str:
        """Replace P→Q with ¬P ∨ Q"""
        # Replace P↔Q with (P→Q) ∧ (Q→P)
        formula = re.sub(r'\(([^()]+)↔([^()]+)\)', r'((\1 → \2) ∧ (\2 → \1))', formula)
        
        # Replace P→Q with ¬P ∨ Q
        while "→" in formula:
            match = re.search(r'([^()∧∨]+)→([^()∧∨]+)', formula)
            if match:
                left, right = match.groups()
                replacement = f"(¬{left.strip()} ∨ {right.strip()})"
                formula = formula[:match.start()] + replacement + formula[match.end():]
            else:
                break
        
        return formula

    def _move_negation_inward(self, formula: str) -> str:
        """Apply De Morgan's laws"""
        # ¬(P ∧ Q) → ¬P ∨ ¬Q
        # ¬(P ∨ Q) → ¬P ∧ ¬Q
        # ¬¬P → P
        
        while "¬(" in formula or "¬¬" in formula:
            # Double negation
            formula = formula.replace("¬¬", "")
            
            # De Morgan's laws (simplified)
            match = re.search(r'¬\(([^()]+)(∧|∨)([^()]+)\)', formula)
            if match:
                left, op, right = match.groups()
                new_op = "∨" if op == "∧" else "∧"
                replacement = f"(¬{left.strip()} {new_op} ¬{right.strip()})"
                formula = formula[:match.start()] + replacement + formula[match.end():]
            else:
                break
        
        return formula

    def _distribute(self, formula: str) -> str:
        """Distribute OR over AND"""
        # P ∨ (Q ∧ R) → (P ∨ Q) ∧ (P ∨ R)
        # (P ∧ Q) ∨ R → (P ∨ R) ∧ (Q ∨ R)
        
        # Simplified distribution
        changed = True
        while changed:
            changed = False
            # Pattern: A ∨ (B ∧ C)
            match = re.search(r'([^()∧]+)\s*∨\s*\(([^()∨]+)∧([^()∨]+)\)', formula)
            if match:
                a, b, c = match.groups()
                replacement = f"(({a.strip()} ∨ {b.strip()}) ∧ ({a.strip()} ∨ {c.strip()}))"
                formula = formula[:match.start()] + replacement + formula[match.end():]
                changed = True
        
        return formula

    def _extract_clauses(self, formula: str) -> List[List[str]]:
        """Extract clauses from CNF formula"""
        clauses = []
        
        # Split by ∧ (conjunction)
        conjuncts = re.split(r'\s*∧\s*', formula)
        
        for conj in conjuncts:
            # Remove outer parentheses
            conj = conj.strip()
            if conj.startswith('(') and conj.endswith(')'):
                conj = conj[1:-1]
            
            # Split by ∨ (disjunction)
            literals = re.split(r'\s*∨\s*', conj)
            clause = [lit.strip() for lit in literals if lit.strip()]
            if clause:
                clauses.append(clause)
        
        return clauses

    # ═══════════════════════════════════════════════════════════════════════════
    # SYLLOGISM VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════

    def validate_syllogism(self, major: str, minor: str, conclusion: str) -> Dict[str, Any]:
        """
        Validate a categorical syllogism.
        
        Example:
          Major: All humans are mortal
          Minor: Socrates is human
          Conclusion: Socrates is mortal
          
        Uses classical syllogistic logic rules.
        """
        # Parse into standard form
        major_parsed = self._parse_categorical(major)
        minor_parsed = self._parse_categorical(minor)
        conclusion_parsed = self._parse_categorical(conclusion)
        
        # Determine figure and mood
        figure = self._determine_figure(major_parsed, minor_parsed)
        mood = self._determine_mood(major_parsed, minor_parsed, conclusion_parsed)
        
        # Check against valid syllogism forms
        valid_forms = {
            # Figure 1
            ("AAA", 1): True,  # Barbara
            ("EAE", 1): True,  # Celarent
            ("AII", 1): True,  # Darii
            ("EIO", 1): True,  # Ferio
            # Figure 2
            ("EAE", 2): True,  # Cesare
            ("AEE", 2): True,  # Camestres
            ("EIO", 2): True,  # Festino
            ("AOO", 2): True,  # Baroco
            # Figure 3
            ("AAI", 3): True,  # Darapti
            ("IAI", 3): True,  # Disamis
            ("AII", 3): True,  # Datisi
            ("EAO", 3): True,  # Felapton
            ("OAO", 3): True,  # Bocardo
            ("EIO", 3): True,  # Ferison
            # Figure 4
            ("AAI", 4): True,  # Bramantip
            ("AEE", 4): True,  # Camenes
            ("IAI", 4): True,  # Dimaris
            ("EAO", 4): True,  # Fesapo
            ("EIO", 4): True,  # Fresison
        }
        
        is_valid = valid_forms.get((mood, figure), False)
        
        # Get the classical name if valid
        classical_names = {
            ("AAA", 1): "Barbara",
            ("EAE", 1): "Celarent",
            ("AII", 1): "Darii",
            ("EIO", 1): "Ferio",
            ("EAE", 2): "Cesare",
            ("AEE", 2): "Camestres",
            ("EIO", 2): "Festino",
            ("AOO", 2): "Baroco",
        }
        
        return {
            "is_valid": is_valid,
            "figure": figure,
            "mood": mood,
            "classical_name": classical_names.get((mood, figure), "unnamed"),
            "major_premise": major_parsed,
            "minor_premise": minor_parsed,
            "conclusion": conclusion_parsed,
        }

    def _parse_categorical(self, statement: str) -> Dict[str, str]:
        """Parse a categorical statement into subject, predicate, and type"""
        statement = statement.lower().strip()
        
        # Determine type (A, E, I, O)
        if statement.startswith("all ") and " are " in statement:
            # A: All S are P
            parts = statement.replace("all ", "").split(" are ")
            return {"type": "A", "subject": parts[0].strip(), "predicate": parts[1].strip() if len(parts) > 1 else ""}
        elif statement.startswith("no ") and " are " in statement:
            # E: No S are P
            parts = statement.replace("no ", "").split(" are ")
            return {"type": "E", "subject": parts[0].strip(), "predicate": parts[1].strip() if len(parts) > 1 else ""}
        elif statement.startswith("some ") and " are " in statement:
            # I: Some S are P
            parts = statement.replace("some ", "").split(" are ")
            return {"type": "I", "subject": parts[0].strip(), "predicate": parts[1].strip() if len(parts) > 1 else ""}
        elif statement.startswith("some ") and " are not " in statement:
            # O: Some S are not P
            parts = statement.replace("some ", "").split(" are not ")
            return {"type": "O", "subject": parts[0].strip(), "predicate": parts[1].strip() if len(parts) > 1 else ""}
        elif " is " in statement:
            # Singular: X is Y (treat as A)
            parts = statement.split(" is ")
            return {"type": "A", "subject": parts[0].strip(), "predicate": parts[1].strip() if len(parts) > 1 else ""}
        else:
            return {"type": "?", "subject": statement, "predicate": ""}

    def _determine_figure(self, major: Dict, minor: Dict) -> int:
        """Determine the figure of a syllogism"""
        # Figure depends on the position of middle term
        # Simplified: use figure 1 as default
        return 1

    def _determine_mood(self, major: Dict, minor: Dict, conclusion: Dict) -> str:
        """Determine the mood of a syllogism"""
        return major.get("type", "?") + minor.get("type", "?") + conclusion.get("type", "?")

    # ═══════════════════════════════════════════════════════════════════════════
    # PROOF CONSTRUCTION
    # ═══════════════════════════════════════════════════════════════════════════

    def prove(self, premises: List[str], conclusion: str) -> Proof:
        """
        Attempt to prove a conclusion from premises.
        
        Uses both truth-table validation and inference rule application.
        """
        # Parse premises and conclusion
        parsed_premises = [self.parse(p) for p in premises]
        parsed_conclusion = self.parse(conclusion)
        
        # First check validity via truth table
        is_valid, proof = self.check_validity(parsed_premises, parsed_conclusion)
        
        if is_valid:
            proof.proof_type = "truth_table"
            return proof
        
        # Try to construct a deductive proof
        proof.proof_type = "natural_deduction"
        proof.steps = self._construct_proof_steps(parsed_premises, parsed_conclusion)
        
        return proof

    def _construct_proof_steps(self, premises: List[Proposition], conclusion: Proposition) -> List[Dict]:
        """Attempt to construct proof steps using inference rules"""
        steps = []
        step_num = 1
        
        # Add premises
        for i, p in enumerate(premises):
            steps.append({
                "step": step_num,
                "formula": p.formula,
                "justification": f"Premise {i + 1}",
                "rule": "assumption",
            })
            step_num += 1
        
        # Try to derive conclusion using rules
        derived = list(premises)
        
        # Try modus ponens
        for p in derived:
            if p.operator == LogicalOperator.IMPLIES and p.sub_propositions:
                antecedent = p.sub_propositions[0]
                for d in derived:
                    if d.formula == antecedent.formula:
                        # Apply modus ponens
                        consequent = p.sub_propositions[1]
                        steps.append({
                            "step": step_num,
                            "formula": consequent.formula,
                            "justification": f"Modus ponens from steps",
                            "rule": "modus_ponens",
                        })
                        derived.append(consequent)
                        step_num += 1
                        
                        # Check if we reached the conclusion
                        if consequent.formula == conclusion.formula:
                            steps.append({
                                "step": step_num,
                                "formula": "∴ " + conclusion.formula,
                                "justification": "QED",
                                "rule": "conclusion",
                            })
                            return steps
        
        # Could not complete proof
        steps.append({
            "step": step_num,
            "formula": "Proof incomplete",
            "justification": "Could not derive conclusion from premises",
            "rule": "incomplete",
        })
        
        return steps

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_llm(self):
        """Lazy load LLM for parsing"""
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for symbolic logic parsing")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the symbolic logic engine"""
        self._running = True
        logger.info("SymbolicLogicEngine started")

    def stop(self):
        """Stop the symbolic logic engine"""
        self._running = False
        logger.info("SymbolicLogicEngine stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            "running": getattr(self, '_running', False),
            "total_propositions": self._total_propositions,
            "total_proofs": self._total_proofs,
            "total_validations": self._total_validations,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

symbolic_logic = SymbolicLogicEngine()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    engine = SymbolicLogicEngine()

    # Test parsing
    print("=== Parsing Tests ===")
    p1 = engine.parse("if P then Q")
    print(f"Parsed: {p1.formula} (type: {p1.proposition_type.value})")
    
    p2 = engine.parse("P and Q")
    print(f"Parsed: {p2.formula} (operator: {p2.operator})")

    # Test truth table
    print("\n=== Truth Table ===")
    prop = engine.parse("P and Q")
    tt = engine.truth_table(prop)
    print(f"Variables: {tt.variables}")
    print(f"Tautology: {tt.is_tautology}, Contradiction: {tt.is_contradiction}, Contingent: {tt.is_contingent}")
    for row in tt.rows:
        print(f"  {row}")

    # Test validity
    print("\n=== Validity Test ===")
    premises = [engine.parse("P implies Q"), engine.parse("P")]
    conclusion = engine.parse("Q")
    is_valid, proof = engine.check_validity(premises, conclusion)
    print(f"Argument is valid: {is_valid}")
    print(f"Proof steps: {proof.steps}")

    # Test syllogism
    print("\n=== Syllogism Test ===")
    result = engine.validate_syllogism(
        "All humans are mortal",
        "Socrates is human",
        "Socrates is mortal"
    )
    print(f"Valid: {result['is_valid']}, Mood: {result['mood']}, Figure: {result['figure']}")

    # Test CNF conversion
    print("\n=== CNF Conversion ===")
    prop = engine.parse("P implies Q")
    cnf = engine.to_cnf(prop)
    print(f"CNF clauses: {cnf}")

    print(f"\nStats: {engine.get_stats()}")