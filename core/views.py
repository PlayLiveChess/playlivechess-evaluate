from django.http import JsonResponse
from django.conf import settings
import chess
import chess.engine
import json


def eval_fen(request):
    try:
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        position = body['position']
        board = chess.Board(position)
        engine = settings.STOCKFISH_ENGINE
    except:
        return JsonResponse({
            'error': 'Invalid position!'
        })
    info = engine.analyse(board, chess.engine.Limit(time=settings.ANALYSIS_TIME))
    print(info['score'].white().wdl().expectation())

    return JsonResponse({
        'score': info['score'].white().wdl().expectation()
    })