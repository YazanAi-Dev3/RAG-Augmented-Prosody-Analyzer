from fastapi import APIRouter, HTTPException
from app.schemas.request import PoemAnalysisRequest
from app.schemas.response import PoemAnalysisResponse, TaskResult
from app.services.structural_analyzer import structural_analyzer
from app.services.rag_engine import rag_engine
from app.services.local_llm import local_llm_engine
from app.services.gemini_fallback import gemini_fallback_engine
from app.core.config import settings
from app.services.diacritizer import diacritizer_engine
router = APIRouter()

@router.post("/analyze", response_model=PoemAnalysisResponse)
async def analyze_poem(request: PoemAnalysisRequest):
    results = {}
    overall_confidence = 1.0
    overall_fail = False

    try:
        # --- The Interceptor: Auto-Diacritization ---
        request.poem_text = diacritizer_engine.diacritize(request.poem_text)
        # 1. Structural Analysis (Meter, Rhyme, Errors)
        structural_tasks = ['meter', 'rhyme', 'errors', 'all']
        if request.task in structural_tasks:
            
            # --- Input Formatting Fix for PyTorch ---
            target_text = request.poem_text
            if request.is_full_poem:
                first_line = request.poem_text.split('\n')[0].strip()
                if '...' in first_line:
                    target_text = first_line
                else:
                    # If lines are separated by newline without '...', join the first two lines
                    lines = [line.strip() for line in request.poem_text.split('\n') if line.strip()]
                    if len(lines) >= 2:
                        target_text = f"{lines[0]} ... {lines[1]}"
                    elif len(lines) == 1:
                        target_text = lines[0]
            
            struct_results = structural_analyzer.analyze(target_text)
            
            if request.task == 'all':
                results.update(struct_results)
            else:
                results[request.task] = struct_results[request.task]

        # 2. Generative & Semantic Analysis (Explanation, Theme)
        generative_tasks = ['explanation_simple', 'explanation_detailed', 'theme', 'question', 'all']
        if request.task in generative_tasks:
            
            llm_result = await local_llm_engine.process_request(
                poem_text=request.poem_text,
                is_full_poem=request.is_full_poem,
                rag_engine=rag_engine
            )
            
            llm_confidence = llm_result.get("confidence", 0.0)
            
            if llm_confidence < settings.CONFIDENCE_THRESHOLD:
                print(f"Local LLM confidence ({llm_confidence}) below threshold. Triggering Gemini Fallback...")
                fallback_context = rag_engine.search(request.poem_text, top_k=4)
                
                llm_result = await gemini_fallback_engine.process_request(
                    target_text=request.poem_text,
                    context=str(fallback_context),
                    is_full_poem=request.is_full_poem
                )
                source_label = "gemini_fallback"
            else:
                source_label = "local_qwen_rag"

            gen_data = {
                "explanation": TaskResult(
                    result=llm_result.get("explanation", ""),
                    confidence=llm_result.get("confidence", 0.0),
                    fail=False if llm_result.get("explanation") else True,
                    source=source_label
                ),
                "theme": TaskResult(
                    result=llm_result.get("theme", ""),
                    confidence=llm_result.get("confidence", 0.0),
                    fail=False if llm_result.get("theme") else True,
                    source=source_label
                )
            }
            
            if request.task == 'all':
                results.update(gen_data)
            elif request.task in ['explanation_simple', 'explanation_detailed']:
                results[request.task] = gen_data["explanation"]
            elif request.task == 'theme':
                results['theme'] = gen_data["theme"]

        # 3. Calculate Overall Status (With Math Fix)
        confidences = []
        for key, res in results.items():
            # Get confidence value whether it's a dict or Pydantic model
            conf = res["confidence"] if isinstance(res, dict) else res.confidence
            
            # Math Fix: If evaluating structural errors and the result is "Safe", 
            # the confidence is the inverse of the error probability.
            if key == 'errors':
                res_val = res["result"] if isinstance(res, dict) else res.result
                if res_val == "سليم":
                    conf = 1.0 - conf
                    
            confidences.append(conf)

        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        overall_fail = any([res["fail"] if isinstance(res, dict) else res.fail for res in results.values()])

        return PoemAnalysisResponse(
            results=results,
            overall_confidence=overall_confidence,
            overall_fail=overall_fail
        )

    except Exception as e:
        print(f"Endpoint Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))