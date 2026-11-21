from nlp.comparison import extract_evidence

def analyze_gaps(chunks):
    evidence=extract_evidence(chunks,limit=5)
    gaps=[]
    limitations=evidence["Limitations"]
    future=evidence["Future work"]
    if limitations:
        gaps.append({"opportunity":"Investigate the limitations reported across the uploaded papers","why":"The authors explicitly describe limitations or unresolved challenges.","evidence":limitations,"research_question":"Can the reported limitation be reduced under a broader set of conditions?"})
    if future:
        gaps.append({"opportunity":"Test author-suggested future directions","why":"Future work is explicitly identified in the uploaded collection.","evidence":future,"research_question":"Do the proposed future directions generalize to additional datasets or settings?"})
    if not gaps:
        gaps.append({"opportunity":"Review underexplored methods, datasets, and evaluation settings in this collection","why":"The available text did not reliably identify explicit limitations or future-work statements.","evidence":[],"research_question":"Which findings remain robust when evaluated on a new dataset or with a complementary method?"})
    return {"label":"Potential research opportunities requiring further literature verification.","gaps":gaps}
