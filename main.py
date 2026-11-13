"""Chemistry Helper: balance chemical equations and calculate yields.

Built with Drafter.  The chemistry math lives in chem.py; this file has
the State, the pages, the routes and the unit tests.
"""
from drafter import *
from dataclasses import dataclass
from chem import (
    split_equation, parse_formula, build_matrix, find_coefficients,
    molar_mass, to_subscript,
)

BALANCE_CHOICE: str = "Balance an equation"
YIELD_CHOICE: str = "Calculate a yield"
REACTANT: str = "reactant"
PRODUCT: str = "product"



@dataclass
class ChemicalComponent:
    """One reactant or product of a chemical equation."""
    name: str
    role: str
    coefficient: int
    elements: dict[str, int]


@dataclass
class State:
    """Everything the site remembers between pages."""
    equation_text: str
    balanced_equation: str
    components: list[ChemicalComponent]
    starting_amount: float
    actual_yield: float
    calculated_yield: float
    explanation: str
    reactant_choice: str
    product_choice: str
    show_details: bool


def new_state() -> State:
    """Return a blank State (used at startup and in the tests)."""
    return State("", "", [], 0.0, 0.0, 0.0, "", "", "", False)


def parse_number(text: str) -> float:
    """Turn text into a float, or return 0.0 if it is not a usable number.

    Blank text, words, "nan", "inf" and absurdly large values give 0.0.
    """
    try:
        value = float(text.strip())
    except ValueError:
        return 0.0
    if value != value or value > 1000000000000.0:
        return 0.0
    return value


def format_number(value: float, places: int) -> str:
    """Round a number for display."""
    return str(round(value, places))

def build_components(equation_text: str) -> list[ChemicalComponent]:
    """Balance the equation and return one component per formula.

    Raises ValueError (with a friendly message) if it cannot be done.
    """
    reactants, products = split_equation(equation_text)
    reactant_counts = []
    for formula in reactants:
        reactant_counts.append(parse_formula(formula))
    product_counts = []
    for formula in products:
        product_counts.append(parse_formula(formula))
    matrix = build_matrix(reactant_counts, product_counts)
    coefficients = find_coefficients(matrix)
    components = []
    position = 0
    for index in range(len(reactants)):
        components.append(ChemicalComponent(
            reactants[index], REACTANT, coefficients[position],
            reactant_counts[index]))
        position += 1
    for index in range(len(products)):
        components.append(ChemicalComponent(
            products[index], PRODUCT, coefficients[position],
            product_counts[index]))
        position += 1
    return components


def format_term(component: ChemicalComponent) -> str:
    """Return the component with its coefficient, e.g. "2 H₂O"."""
    name = to_subscript(component.name)
    if component.coefficient == 1:
        return name
    return str(component.coefficient) + " " + name


def format_equation(components: list[ChemicalComponent]) -> str:
    """Return the balanced equation as text, e.g. "2 H₂ + O₂ → 2 H₂O"."""
    left = []
    right = []
    for component in components:
        if component.role == REACTANT:
            left.append(format_term(component))
        else:
            right.append(format_term(component))
    return " + ".join(left) + " → " + " + ".join(right)


def element_summary(elements: dict[str, int]) -> str:
    """Return atom counts as text, e.g. "H: 2, O: 1"."""
    parts = []
    for symbol in sorted(elements):
        parts.append(symbol + ": " + str(elements[symbol]))
    return ", ".join(parts)


def atom_totals(
    components: list[ChemicalComponent], role: str
) -> dict[str, int]:
    """Add up every atom on one side of the equation.

    Loops over each component with the given role and adds its element
    counts multiplied by its coefficient.
    """
    totals = {}
    for component in components:
        if component.role == role:
            for symbol in component.elements:
                amount = component.elements[symbol] * component.coefficient
                totals[symbol] = totals.get(symbol, 0) + amount
    return totals


def names_for_role(
    components: list[ChemicalComponent], role: str
) -> list[str]:
    """Return the formulas of all components with the given role."""
    names = []
    for component in components:
        if component.role == role:
            names.append(component.name)
    return names


def find_component(
    components: list[ChemicalComponent], name: str, role: str
) -> int:
    """Return the index of the component with this name and role.

    Returns -1 if there is no such component.
    """
    for index in range(len(components)):
        match = components[index]
        if match.name == name and match.role == role:
            return index
    return -1


def component_mass(component: ChemicalComponent) -> float:
    """Return the molar mass of one component in g/mol."""
    return molar_mass(component.elements)


def theoretical_grams(
    reactant: ChemicalComponent, product: ChemicalComponent,
    start_grams: float,
) -> float:
    """Return the most product (grams) the starting amount could make."""
    moles = start_grams / component_mass(reactant)
    product_moles = moles * product.coefficient / reactant.coefficient
    return product_moles * component_mass(product)


def percent_yield(actual: float, theoretical: float) -> float:
    """Return actual yield as a percent of the theoretical yield."""
    return actual / theoretical * 100


def describe_yield(state: State) -> str:
    """Return a one-sentence summary of the yield result."""
    percent = percent_yield(state.actual_yield, state.calculated_yield)
    text = (
        "Starting with " + format_number(state.starting_amount, 2)
        + " g of " + to_subscript(state.reactant_choice)
        + ", the theoretical yield of "
        + to_subscript(state.product_choice) + " is "
        + format_number(state.calculated_yield, 2) + " g. Your actual "
        + "yield of " + format_number(state.actual_yield, 2)
        + " g is a " + format_number(percent, 1) + "% yield."
    )
    if percent > 100:
        text += (
            " A yield over 100% usually means the product was impure "
            "or wet, or a measurement was off."
        )
    return text


def component_lines(components: list[ChemicalComponent]) -> list[str]:
    """Return one description line for every component."""
    lines = []
    for component in components:
        lines.append(
            format_term(component) + " (" + component.role
            + "), molar mass " + format_number(component_mass(component), 2)
            + " g/mol"
        )
    return lines


def balance_details(components: list[ChemicalComponent]) -> list[str]:
    """Return the steps that show why the equation is balanced."""
    lines = []
    for component in components:
        lines.append(
            to_subscript(component.name) + " has "
            + element_summary(component.elements)
            + " atoms in each molecule; the coefficient is "
            + str(component.coefficient) + "."
        )
    left = atom_totals(components, REACTANT)
    right = atom_totals(components, PRODUCT)
    lines.append("Total atoms on the left: " + element_summary(left))
    lines.append("Total atoms on the right: " + element_summary(right))
    if left == right:
        lines.append("Both sides match, so the equation is balanced.")
    else:
        lines.append("The sides do not match, so something is wrong.")
    return lines


def yield_details(state: State) -> list[str]:
    """Return the steps used to find the yield (empty if none yet)."""
    reactant_index = find_component(
        state.components, state.reactant_choice, REACTANT)
    product_index = find_component(
        state.components, state.product_choice, PRODUCT)
    if state.calculated_yield <= 0 or reactant_index == -1:
        return []
    if product_index == -1:
        return []
    reactant = state.components[reactant_index]
    product = state.components[product_index]
    reactant_mass = component_mass(reactant)
    product_mass = component_mass(product)
    moles = state.starting_amount / reactant_mass
    product_moles = moles * product.coefficient / reactant.coefficient
    r_name = to_subscript(reactant.name)
    p_name = to_subscript(product.name)
    percent = percent_yield(state.actual_yield, state.calculated_yield)
    return [
        "Molar mass of " + r_name + " = "
        + format_number(reactant_mass, 2) + " g/mol.",
        "Moles of " + r_name + " = " + format_number(state.starting_amount, 2)
        + " g ÷ " + format_number(reactant_mass, 2) + " g/mol = "
        + format_number(moles, 4) + " mol.",
        "The equation makes " + str(product.coefficient) + " " + p_name
        + " for every " + str(reactant.coefficient) + " " + r_name
        + ", so moles of " + p_name + " = " + format_number(product_moles, 4)
        + " mol.",
        "Theoretical yield = " + format_number(product_moles, 4)
        + " mol × " + format_number(product_mass, 2) + " g/mol = "
        + format_number(state.calculated_yield, 2) + " g.",
        "Percent yield = " + format_number(state.actual_yield, 2) + " g ÷ "
        + format_number(state.calculated_yield, 2) + " g × 100 = "
        + format_number(percent, 1) + "%.",
    ]



def make_balance_page(state: State, message: str) -> Page:
    """Build the balance page, showing a warning if message is not blank."""
    content = [
        Header("Balance an Equation"),
        "Type an equation using an arrow, like: C3H8 + O2 -> CO2 + H2O",
        "Capital letters matter (Co is cobalt, CO is carbon monoxide). "
        "Parentheses like Ca(OH)2 work too.",
        TextBox("equation_text", state.equation_text),
        LineBreak(),
    ]
    if message != "":
        content.append("⚠ " + message)
    content.append(Button("Balance it!", balance_equation))
    content.append(Button("Back to home", return_home))
    return Page(state, content)


def make_yield_page(state: State, message: str) -> Page:
    """Build the yield page, showing a warning if message is not blank."""
    if len(state.components) == 0:
        return Page(state, [
            Header("Yield Calculator"),
            "To find a yield, first balance an equation so the site "
            "knows the mole ratios.",
            Button("Balance an equation", balance_page),
            Button("Back to home", return_home),
        ])
    reactants = names_for_role(state.components, REACTANT)
    products = names_for_role(state.components, PRODUCT)
    reactant_default = state.reactant_choice
    if reactant_default not in reactants:
        reactant_default = reactants[0]
    product_default = state.product_choice
    if product_default not in products:
        product_default = products[0]
    start_default = ""
    if state.starting_amount > 0:
        start_default = str(state.starting_amount)
    actual_default = ""
    if state.actual_yield > 0:
        actual_default = str(state.actual_yield)
    content = [
        Header("Yield Calculator"),
        "Balanced equation: " + state.balanced_equation,
        "Which reactant did you start with?",
        SelectBox("reactant_name", reactants, reactant_default),
        "How many grams of it did you start with?",
        TextBox("starting_amount", start_default),
        "Which product did you make?",
        SelectBox("product_name", products, product_default),
        "How many grams of it did you actually get?",
        TextBox("actual_yield", actual_default),
        LineBreak(),
    ]
    if message != "":
        content.append("⚠ " + message)
    content.append(Button("Calculate yield", calculate_yield))
    content.append(Button("Back to home", return_home))
    return Page(state, content)



@route
def index(state: State) -> Page:
    """Home page: pick whether to balance an equation or find a yield."""
    return Page(state, [
        Header("Chemistry Helper"),
        "Balance chemical equations and calculate chemical yields, with "
        "a short explanation of every result.",
        "What would you like to do?",
        SelectBox(
            "calc_type", [BALANCE_CHOICE, YIELD_CHOICE], BALANCE_CHOICE),
        Button("Continue", choose_tool),
    ])


@route
def balance_page(state: State) -> Page:
    """Page with a box to type an equation to balance."""
    return make_balance_page(state, "")


@route
def yield_page(state: State) -> Page:
    """Page that asks for the amounts used in a yield calculation."""
    return make_yield_page(state, "")


@route
def results_page(state: State) -> Page:
    """Show the balanced equation and, if there is one, the yield."""
    if state.balanced_equation == "":
        return Page(state, [
            Header("Results"),
            "There is nothing to show yet.",
            Button("Balance an equation", balance_page),
            Button("Back to home", return_home),
        ])
    content = [
        Header("Results"),
        Header("Balanced equation", 2),
        state.balanced_equation,
        BulletedList(component_lines(state.components)),
    ]
    if state.calculated_yield > 0:
        percent = percent_yield(state.actual_yield, state.calculated_yield)
        content.append(Header("Yield", 2))
        content.append(BulletedList([
            "Theoretical yield of " + to_subscript(state.product_choice)
            + ": " + format_number(state.calculated_yield, 2) + " g",
            "Actual yield: " + format_number(state.actual_yield, 2) + " g",
            "Percent yield: " + format_number(percent, 1) + "%",
        ]))
    else:
        content.append(
            "No yield has been calculated yet. Try the yield calculator!")
    content.append(Button("How did you get this?", explanation_page))
    content.append(Button("Calculate a yield", yield_page))
    content.append(Button("Balance another equation", balance_page))
    content.append(Button("Back to home", return_home))
    return Page(state, content)


@route
def explanation_page(state: State) -> Page:
    """Explain the result, with a button to show or hide the details."""
    if len(state.components) == 0:
        return Page(state, [
            Header("Explanation"),
            "Balance an equation first and then I can explain it.",
            Button("Back to home", return_home),
        ])
    summary = state.explanation
    if summary == "":
        summary = "Review the steps below."
    content = [Header("Explanation"), summary]
    if state.show_details:
        content.append(Header("How the equation was balanced", 2))
        content.append(BulletedList(balance_details(state.components)))
        steps = yield_details(state)
        if len(steps) > 0:
            content.append(Header("How the yield was calculated", 2))
            content.append(BulletedList(steps))
        content.append(Button("Hide details", toggle_explanation))
    else:
        content.append(Button("Show details", toggle_explanation))
    content.append(Button("Back to results", results_page))
    content.append(Button("Back to home", return_home))
    return Page(state, content)


@route
def choose_tool(state: State, calc_type: str) -> Page:
    """Send the user to the page for the tool they picked on the home page."""
    if calc_type == BALANCE_CHOICE:
        return balance_page(state)
    return yield_page(state)


@route
def balance_equation(state: State, equation_text: str) -> Page:
    """Balance the typed equation and save the result in the State."""
    state.equation_text = equation_text
    if equation_text.strip() == "":
        return make_balance_page(state, "Please type an equation first.")
    try:
        components = build_components(equation_text)
    except ValueError as problem:
        return make_balance_page(state, str(problem))
    state.components = components
    state.balanced_equation = format_equation(components)
    state.starting_amount = 0.0
    state.actual_yield = 0.0
    state.calculated_yield = 0.0
    state.reactant_choice = ""
    state.product_choice = ""
    state.show_details = False
    state.explanation = (
        "The equation is balanced when every element has the same number "
        "of atoms on both sides. I found the smallest whole-number "
        "coefficients that make that true."
    )
    return results_page(state)


@route
def calculate_yield(
    state: State, reactant_name: str, product_name: str,
    starting_amount: str, actual_yield: str,
) -> Page:
    """Calculate the theoretical and percent yield and save them."""
    start = parse_number(starting_amount)
    actual = parse_number(actual_yield)
    if start <= 0 or actual <= 0:
        return make_yield_page(
            state, "Both amounts must be numbers greater than zero.")
    reactant_index = find_component(state.components, reactant_name, REACTANT)
    product_index = find_component(state.components, product_name, PRODUCT)
    if reactant_index == -1 or product_index == -1:
        return make_yield_page(
            state, "Please choose a reactant and a product.")
    state.starting_amount = start
    state.actual_yield = actual
    state.reactant_choice = reactant_name
    state.product_choice = product_name
    state.calculated_yield = theoretical_grams(
        state.components[reactant_index],
        state.components[product_index], start)
    state.explanation = describe_yield(state)
    state.show_details = False
    return results_page(state)


@route
def toggle_explanation(state: State) -> Page:
    """Flip between showing and hiding the detailed steps."""
    state.show_details = not state.show_details
    return explanation_page(state)


@route
def return_home(state: State) -> Page:
    """Go back to the home page."""
    state.show_details = False
    return index(state)

# Unit tests

assert_equal(parse_number("12.5"), 12.5)
assert_equal(parse_number(" 3 "), 3.0)
assert_equal(parse_number("abc"), 0.0)
assert_equal(parse_number(""), 0.0)
assert_equal(parse_number("nan"), 0.0)
assert_equal(format_number(3.14159, 2), "3.14")

assert_equal(to_subscript("H2O"), "H₂O")
assert_equal(to_subscript("Ca(OH)2"), "Ca(OH)₂")
assert_equal(format_equation(build_components("H2 + O2 -> H2O")),
             "2 H₂ + O₂ → 2 H₂O")
assert_equal(format_equation(build_components("Fe + O2 = Fe2O3")),
             "4 Fe + 3 O₂ → 2 Fe₂O₃")
assert_equal(
    format_equation(build_components("Ca(OH)2 + H3PO4 -> Ca3(PO4)2 + H2O")),
    "3 Ca(OH)₂ + 2 H₃PO₄ → Ca₃(PO₄)₂ + 6 H₂O")
assert_equal(
    format_equation(build_components("C3H8 + O2 -> CO2 + H2O")),
    "C₃H₈ + 5 O₂ → 3 CO₂ + 4 H₂O")

assert_equal(
    element_summary({"O": 1, "H": 2}), "H: 2, O: 1")
assert_equal(
    atom_totals(build_components("H2 + O2 -> H2O"), REACTANT),
    {"H": 4, "O": 2})
assert_equal(
    atom_totals(build_components("H2 + O2 -> H2O"), PRODUCT),
    {"H": 4, "O": 2})
assert_equal(
    names_for_role(build_components("H2 + O2 -> H2O"), PRODUCT), ["H2O"])
assert_equal(
    find_component(build_components("H2 + O2 -> H2O"), "O2", REACTANT), 1)
assert_equal(
    find_component(build_components("H2 + O2 -> H2O"), "O2", PRODUCT), -1)
assert_equal(
    format_number(
        component_mass(build_components("H2 + O2 -> H2O")[2]), 2), "18.02")
assert_equal(
    format_number(
        theoretical_grams(
            build_components("H2 + O2 -> H2O")[0],
            build_components("H2 + O2 -> H2O")[2], 4.032), 2), "36.03")
assert_equal(percent_yield(45.0, 90.0), 50.0)
assert_equal(
    balance_details(build_components("H2 + O2 -> H2O"))[-1],
    "Both sides match, so the equation is balanced.")
assert_equal(yield_details(new_state()), [])


assert_equal(
    balance_equation(new_state(), "H2 + O2 -> H2O").state.balanced_equation,
    "2 H₂ + O₂ → 2 H₂O")
assert_equal(
    len(balance_equation(new_state(), "H2 + O2 -> H2O").state.components),
    3)
assert_equal(
    balance_equation(new_state(), "   ").state.balanced_equation, "")
assert_equal(
    balance_equation(new_state(), "H2 -> H2O").state.components, [])
assert_equal(
    balance_equation(new_state(), "Xx + O2 -> XxO").state.components, [])
assert_equal(
    balance_equation(new_state(), "H2 + O2").state.equation_text,
    "H2 + O2")

assert_equal(
    calculate_yield(
        balance_equation(new_state(), "H2 + O2 -> H2O").state,
        "H2", "H2O", "4.032", "30").state.calculated_yield > 36.0, True)
assert_equal(
    calculate_yield(
        balance_equation(new_state(), "H2 + O2 -> H2O").state,
        "H2", "H2O", "", "30").state.calculated_yield, 0.0)
assert_equal(
    calculate_yield(
        balance_equation(new_state(), "H2 + O2 -> H2O").state,
        "H2", "H2O", "-5", "30").state.calculated_yield, 0.0)
assert_equal(
    calculate_yield(
        balance_equation(new_state(), "H2 + O2 -> H2O").state,
        "H2", "O2", "5", "30").state.calculated_yield, 0.0)
assert_equal(
    calculate_yield(
        balance_equation(new_state(), "H2 + O2 -> H2O").state,
        "H2", "H2O", "4.032", "30").state.starting_amount, 4.032)

assert_equal(toggle_explanation(new_state()).state.show_details, True)
assert_equal(
    toggle_explanation(toggle_explanation(new_state()).state)
    .state.show_details, False)
assert_equal(return_home(
    toggle_explanation(new_state()).state).state.show_details, False)
assert_equal(choose_tool(new_state(), BALANCE_CHOICE).state.components, [])
assert_equal(choose_tool(new_state(), YIELD_CHOICE).state.components, [])

set_website_title("Chemistry Helper")
set_site_information(
    author="Elena Lewis",
    description="Balance chemical equations and calculate percent yield.",
    sources=[
        "Drafter documentation: https://drafter-edu.github.io/drafter/",
        "LLM conversation: llm_conversation.md",
    ],
    planning=["compsci_projectdesign.pdf"],
    links=["https://github.com/ellewis-723/chemistry-helper"],
)
hide_debug_information()
set_website_framed(False)
start_server(new_state())

"""PASTED BELOW IS MY CHEM.PY FILE THAT IS USED ++++++++++
**********ADVANCED TECHNIQUE (not covered in class): 
balancing an equation is done
with linear algebra.  Each species (reactant or product) is a column of a
matrix and each element is a row; the entry is how many atoms of that
element are in one molecule (products are negative).  A set of
coefficients balances the equation when the matrix times the coefficients
equals zero."""

ATOMIC_MASSES: dict[str, float] = {
    "H": 1.008, "He": 4.0026, "Li": 6.94, "Be": 9.0122, "B": 10.81,
    "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998, "Ne": 20.180,
    "Na": 22.990, "Mg": 24.305, "Al": 26.982, "Si": 28.085,
    "P": 30.974, "S": 32.06, "Cl": 35.45, "Ar": 39.948, "K": 39.098,
    "Ca": 40.078, "Sc": 44.956, "Ti": 47.867, "V": 50.942,
    "Cr": 51.996, "Mn": 54.938, "Fe": 55.845, "Co": 58.933,
    "Ni": 58.693, "Cu": 63.546, "Zn": 65.38, "Ga": 69.723,
    "Ge": 72.630, "As": 74.922, "Se": 78.971, "Br": 79.904,
    "Kr": 83.798, "Rb": 85.468, "Sr": 87.62, "Ag": 107.87,
    "Sn": 118.71, "I": 126.90, "Ba": 137.33, "W": 183.84,
    "Pt": 195.08, "Au": 196.97, "Hg": 200.59, "Pb": 207.2,
    "U": 238.03,
}
ARROWS: list[str] = ["<->", "-->", "->", "=>", "→", "="]
SUBSCRIPT_DIGITS: str = "₀₁₂₃₄₅₆₇₈₉"
DIGITS: str = "0123456789"


def gcd(first: int, second: int) -> int:
    """Return the greatest common divisor of two whole numbers."""
    first = abs(first)
    second = abs(second)
    while second != 0:
        first, second = second, first % second
    return first


def lcm(first: int, second: int) -> int:
    """Return the least common multiple of two positive whole numbers."""
    return first // gcd(first, second) * second


def to_subscript(formula: str) -> str:
    """Return the formula with every digit written as a subscript.

    Example: "H2O" becomes "H₂O".
    """
    result = ""
    for character in formula:
        if character in DIGITS:
            result += SUBSCRIPT_DIGITS[DIGITS.index(character)]
        else:
            result += character
    return result


def strip_coefficient(term: str) -> str:
    """Remove spaces and any leading coefficient from one term.

    Example: " 2 H2O" becomes "H2O".
    """
    squeezed = "".join(term.split())
    position = 0
    while position < len(squeezed) and squeezed[position] in DIGITS:
        position += 1
    return squeezed[position:]


def split_side(side: str) -> list[str]:
    """Split one side of an equation into its formulas.

    Raises ValueError if a formula is missing (like "H2 + -> H2O").
    """
    formulas = []
    for term in side.split("+"):
        formula = strip_coefficient(term)
        if formula == "":
            raise ValueError(
                "Each side needs formulas separated by + signs."
            )
        formulas.append(formula)
    return formulas


def split_equation(text: str) -> tuple[list[str], list[str]]:
    """Split equation text into (reactant formulas, product formulas).

    Accepts ->, -->, =>, = or → as the arrow.
    Raises ValueError if there is not exactly one arrow.
    """
    cleaned = text
    for arrow in ARROWS:
        cleaned = cleaned.replace(arrow, "~")
    if cleaned.count("~") != 1:
        raise ValueError(
            "Use exactly one arrow, like H2 + O2 -> H2O."
        )
    sides = cleaned.split("~")
    return split_side(sides[0]), split_side(sides[1])


def read_number(text: str, start: int) -> tuple[int, int]:
    """Read a whole number starting at position start.

    Returns (number, next position).  If there are no digits the number
    is 1, because "O" means the same as "O1" in a formula.
    """
    position = start
    while position < len(text) and text[position] in DIGITS:
        position += 1
    if position == start:
        return 1, start
    return int(text[start:position]), position


def add_atoms(counts: dict[str, int], symbol: str, amount: int) -> None:
    """Add amount atoms of symbol into the counts dictionary."""
    counts[symbol] = counts.get(symbol, 0) + amount


def parse_formula(formula: str) -> dict[str, int]:
    """Count the atoms of each element in a formula.

    Deals with parentheses, so "Ca(OH)2" gives {"Ca": 1, "O": 2, "H": 2}.
    Uses a stack: every "(" starts a new group of counts and every ")"
    multiplies that group and merges it into the group below it.
    Raises ValueError for unknown elements or bad characters.
    """
    stack = [{}]
    position = 0
    while position < len(formula):
        character = formula[position]
        if character == "(":
            stack.append({})
            position += 1
        elif character == ")":
            if len(stack) < 2:
                raise ValueError("Unmatched ) in " + formula + ".")
            group = stack.pop()
            amount, position = read_number(formula, position + 1)
            if amount == 0:
                raise ValueError("A subscript cannot be 0.")
            for symbol in group:
                add_atoms(stack[-1], symbol, group[symbol] * amount)
        elif character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            symbol = character
            position += 1
            if position < len(formula) and formula[position].islower():
                symbol += formula[position]
                position += 1
            if symbol not in ATOMIC_MASSES:
                raise ValueError(
                    "I don't know the element " + symbol + " in "
                    + formula + ". Check your capital letters."
                )
            amount, position = read_number(formula, position)
            if amount == 0:
                raise ValueError("A subscript cannot be 0.")
            add_atoms(stack[-1], symbol, amount)
        else:
            raise ValueError(
                "Unexpected '" + character + "' in " + formula + "."
            )
    if len(stack) != 1:
        raise ValueError("Unmatched ( in " + formula + ".")
    return stack[0]


def molar_mass(elements: dict[str, int]) -> float:
    """Return the molar mass (g/mol) for a dictionary of atom counts."""
    total = 0.0
    for symbol in elements:
        total += ATOMIC_MASSES[symbol] * elements[symbol]
    return total


def build_matrix(
    reactants: list[dict[str, int]], products: list[dict[str, int]]
) -> list[list[int]]:
    """Build the atom-count matrix (one row per element).

    Reactant columns are positive, product columns are negative.
    """
    symbols = []
    for species in reactants + products:
        for symbol in species:
            if symbol not in symbols:
                symbols.append(symbol)
    matrix = []
    for symbol in symbols:
        row = []
        for species in reactants:
            row.append(species.get(symbol, 0))
        for species in products:
            row.append(-species.get(symbol, 0))
        matrix.append(row)
    return matrix


def reduce_row(row: list[int]) -> list[int]:
    """Divide a row by the gcd of its entries to keep numbers small."""
    divisor = 0
    for value in row:
        divisor = gcd(divisor, value)
    if divisor > 1:
        return [value // divisor for value in row]
    return row


def row_reduce(matrix: list[list[int]]) -> tuple[list[list[int]], list[int]]:
    """elimination using only whole numbers.

    Returns (reduced rows, list of pivot columns).  Each pivot column has
    exactly one non-zero entry (the pivot) after reduction.
    """
    rows = [row[:] for row in matrix]
    pivots = []
    pivot_row = 0
    for column in range(len(rows[0])):
        if pivot_row >= len(rows):
            break
        found = -1
        for candidate in range(pivot_row, len(rows)):
            if rows[candidate][column] != 0:
                found = candidate
                break
        if found == -1:
            continue
        rows[pivot_row], rows[found] = rows[found], rows[pivot_row]
        pivot_value = rows[pivot_row][column]
        for other in range(len(rows)):
            factor = rows[other][column]
            if other != pivot_row and factor != 0:
                for spot in range(len(rows[other])):
                    rows[other][spot] = (
                        rows[other][spot] * pivot_value
                        - rows[pivot_row][spot] * factor
                    )
                rows[other] = reduce_row(rows[other])
        pivots.append(column)
        pivot_row += 1
    return rows, pivots


def find_coefficients(matrix: list[list[int]]) -> list[int]:
    """Return the smallest whole-number coefficients that balance.

    Raises ValueError if the equation cannot be balanced, or if there is
    more than one way to balance it.
    """
    rows, pivots = row_reduce(matrix)
    free_columns = []
    for column in range(len(matrix[0])):
        if column not in pivots:
            free_columns.append(column)
    if len(free_columns) == 0:
        raise ValueError(
            "This equation cannot be balanced. Check the formulas."
        )
    if len(free_columns) > 1:
        raise ValueError(
            "This equation can be balanced in more than one way. "
            "Check that every formula belongs in the reaction."
        )
    free = free_columns[0]
    scale = 1
    for index in range(len(pivots)):
        pivot_size = abs(rows[index][pivots[index]])
        free_size = abs(rows[index][free])
        scale = lcm(scale, pivot_size // gcd(pivot_size, free_size))
    coefficients = [0] * len(matrix[0])
    coefficients[free] = scale
    for index in range(len(pivots)):
        pivot_value = rows[index][pivots[index]]
        coefficients[pivots[index]] = (
            -rows[index][free] * scale // pivot_value
        )
    return clean_coefficients(coefficients)


def clean_coefficients(coefficients: list[int]) -> list[int]:
    """Make coefficients positive and in lowest terms.

    Raises ValueError if any coefficient would be zero or if the signs
    are mixed (the reaction cannot happen with these formulas).
    """
    if coefficients[0] < 0:
        coefficients = [-value for value in coefficients]
    divisor = 0
    for value in coefficients:
        if value <= 0:
            raise ValueError(
                "This equation cannot be balanced with whole numbers. "
                "Check that each element appears on both sides."
            )
        divisor = gcd(divisor, value)
    return [value // divisor for value in coefficients]
