from django.http import JsonResponse
from django.conf import settings
import chess
import chess.engine
import json
import os

def get_engine():
    """Check if the engine is running, and reopen if necessary."""
    try:
        if settings.STOCKFISH_ENGINE is None or settings.STOCKFISH_ENGINE.protocol.closed:
            settings.STOCKFISH_ENGINE = chess.engine.SimpleEngine.popen_uci(
                os.path.join(settings.BASE_DIR, settings.STOCKFISH_BINARY_PATH)
            )
    except AttributeError:
        # In case STOCKFISH_ENGINE is not initialized
        settings.STOCKFISH_ENGINE = chess.engine.SimpleEngine.popen_uci(
            os.path.join(settings.BASE_DIR, settings.STOCKFISH_BINARY_PATH)
        )

    return settings.STOCKFISH_ENGINE


def eval_fen(request):
    try:
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        position = body['position']
        board = chess.Board(position)
        engine = get_engine()  # Ensure the engine is running
    except:
        return JsonResponse({'error': 'Invalid position!'})

    info = engine.analyse(board, chess.engine.Limit(time=settings.ANALYSIS_TIME))
    return JsonResponse({'score': info['score'].white().wdl().expectation()})


def eval_moves(request):
    try:
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        position = body['position']
        board = chess.Board(position)
        engine = get_engine()  # Ensure the engine is running
    except:
        return JsonResponse({'error': 'Invalid position!'})

    try:
        info = engine.analyse(board, chess.engine.Limit(depth=18))
        pv = info.get('pv', [])
        moves = []
        move_string = ""
        move_number = 1
        is_white_to_move = board.turn

        if not is_white_to_move:
            move_string = "1. ... "

        for move in pv:
            if len(moves) >= 10:
                break

            san_move = board.san(move)
            moves.append(san_move)

            if is_white_to_move:
                move_string += f"{move_number}. {san_move} "
            else:
                move_string += f"{san_move} "
                move_number += 1

            board.push(move)
            is_white_to_move = not is_white_to_move

        score = info['score'].white().wdl().expectation()
    except Exception as e:
        print(e)
        return JsonResponse({'error': 'Engine analysis failed!'})

    return JsonResponse({'score': score, 'moves': moves, 'move_string': move_string.strip()})
