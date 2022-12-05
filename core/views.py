from django.http import JsonResponse
from django.conf import settings
import chess
import chess.engine


def eval_fen(request):
    board = chess.Board()
    engine = settings.STOCKFISH_ENGINE
    info = engine.analyse(board, chess.engine.Limit(time=settings.ANALYSIS_TIME))
    score = info['score'].white().score()/100

    return JsonResponse({
        'score': score
    })