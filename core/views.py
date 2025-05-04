from django.http import JsonResponse
from django.conf import settings
import chess
import chess.engine
import json
import os
import queue
import threading
import time
from contextlib import contextmanager

# Create a thread-safe engine pool
class StockfishEnginePool:
    def __init__(self, max_engines=4, timeout=30):
        self.max_engines = max_engines
        self.timeout = timeout
        self.engines = queue.Queue(maxsize=max_engines)
        self.lock = threading.Lock()
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize the engine pool with engine instances."""
        for _ in range(self.max_engines):
            engine = self._create_engine()
            self.engines.put(engine)
    
    def _create_engine(self):
        """Create a new engine instance."""
        return chess.engine.SimpleEngine.popen_uci(
            os.path.join(settings.BASE_DIR, settings.STOCKFISH_BINARY_PATH)
        )
    
    @contextmanager
    def get_engine(self):
        """Get an engine from the pool with timeout handling."""
        engine = None
        try:
            engine = self.engines.get(timeout=self.timeout)
            try:
                # Test if engine is responsive
                engine.ping()
                yield engine
            except Exception:
                # If engine is in error state, close it and create new one
                try:
                    engine.quit()
                except Exception:
                    pass
                engine = self._create_engine()
                yield engine
        finally:
            if engine:
                self.engines.put(engine)
    
    def close(self):
        """Close all engines in the pool."""
        with self.lock:
            while not self.engines.empty():
                try:
                    engine = self.engines.get_nowait()
                    try:
                        engine.quit()
                    except Exception:
                        pass
                except queue.Empty:
                    break

# Initialize the engine pool
ENGINE_POOL = StockfishEnginePool(
    max_engines=getattr(settings, 'STOCKFISH_MAX_ENGINES', 4)
)

def eval_fen(request):
    """Evaluate a given FEN position using Stockfish."""
    try:
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        position = body['position']
        board = chess.Board(position)
    except:
        return JsonResponse({'error': 'Invalid position!'})

    try:
        with ENGINE_POOL.get_engine() as engine:
            info = engine.analyse(board, chess.engine.Limit(time=settings.ANALYSIS_TIME))
            return JsonResponse({'score': info['score'].white().wdl().expectation()})
    except queue.Empty:
        return JsonResponse({'error': 'No engine available, server is busy!'})
    except Exception as e:
        return JsonResponse({'error': f'Engine analysis failed: {str(e)}'})


def eval_moves(request):
    """Get the best sequence of moves from Stockfish for a given position."""
    try:
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        position = body['position']
        board = chess.Board(position)
    except:
        return JsonResponse({'error': 'Invalid position!'})

    try:
        with ENGINE_POOL.get_engine() as engine:
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
            return JsonResponse({'score': score, 'moves': moves, 'move_string': move_string.strip()})
    except queue.Empty:
        return JsonResponse({'error': 'No engine available, server is busy!'})
    except Exception as e:
        return JsonResponse({'error': f'Engine analysis failed: {str(e)}'})
