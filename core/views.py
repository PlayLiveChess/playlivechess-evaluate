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

def eval_moves(request):
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
    
    try:
        # Get the engine analysis
        info = engine.analyse(board, chess.engine.Limit(depth=18))
        pv = info.get('pv', [])  # Principal variation (best line), default to empty list if not present
        moves = []
        move_string = ""
        move_number = 1  # Initialize move number
        is_white_to_move = board.turn  # Check if it's white's turn to move
        if not is_white_to_move:
            move_string = "1. ... "

        for move in pv:
            # limit fo 10 moves
            if len(moves) >= 10:
                break

            san_move = board.san(move)  # Convert move to SAN
            moves.append(san_move)  # Append SAN move to the list

            # Construct the move string with numbering
            if is_white_to_move:
                move_string += f"{move_number}. {san_move} "
            else:
                move_string += f"{san_move} "
                move_number += 1  # Increment move number after black's move

            board.push(move)  # Update the board with the move
            is_white_to_move = not is_white_to_move  # Update turn

        score = info['score'].white().wdl().expectation()  # Extract score
    except Exception as e:
        print(e)
        return JsonResponse({
            'error': 'Engine analysis failed!'
        })

    return JsonResponse({
        'score': score,
        'moves': moves,
        'move_string': move_string.strip()
    })
