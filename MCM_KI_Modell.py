import numpy as np
from sklearn.cluster import DBSCAN
import random
from config import Config
# --------------------------------------------------
Default_N_AGENTS = 160
DIMS = 3
# --------------------------------------------------
# Wahrnehmung
# --------------------------------------------------

class Perception:

    def encode(self, stimulus):
        """Stimulus → Energieimpuls"""

        mapping = {
            "positive": +1.45,
            "negative": -0.65,
            "threat": -1.75,
            "reward": +1.55,
            "neutral": 0.0
        }

        return mapping.get(stimulus, 0.0)
    
# --------------------------------------------------
# MCM SelfModel
# --------------------------------------------------
class SelfModel:

    def evaluate(self, energy):

        mean_e = float(np.mean(energy[:,0]))
        motivation = float(np.mean(energy[:,1]))
        risk = float(np.mean(energy[:,2]))

        if risk <= -1.5:
            return "stressed"

        if motivation >= 1.2:
            return "excited"

        if abs(mean_e) < 0.2:
            return "stable"

        return "active"
    
# --------------------------------------------------
# MCM Feld
# --------------------------------------------------

class MCMField:

    def __init__(self, n_agents=Default_N_AGENTS, dims=DIMS):

        self.N = n_agents
        self.D = dims

        self.energy = np.random.uniform(-0.3,0.3,(self.N,self.D))
        self.velocity = np.zeros((self.N,self.D))

        self.k_center = 0.0035
        self.coupling = 0.08
        self.noise = 0.18
        self.coupling_sigma = float(getattr(Config, "MCM_FIELD_COUPLING_SIGMA", 0.5) or 0.5)
        self.local_neighbor_count = max(1, int(getattr(Config, "MCM_FIELD_LOCAL_NEIGHBORS", 8) or 8))

    def step(self, impulse):

        # Energieimpuls nur auf erste Dimension
        self.energy[:,0] += impulse

        # Zentrumskraft
        force = -self.k_center * self.energy

        # lokale Kopplung über sortierte Nachbarschaft statt vollem NxN-Feld
        coupling_force = np.zeros_like(self.energy)
        sigma = max(float(self.coupling_sigma or 0.5), 1e-9)
        local_neighbors = max(1, int(self.local_neighbor_count or 1))

        for d in range(self.D):

            e = self.energy[:,d]
            order = np.argsort(e)
            sorted_e = e[order]
            sorted_force = np.zeros_like(sorted_e)

            for idx in range(len(sorted_e)):

                start = max(0, idx - local_neighbors)
                end = min(len(sorted_e), idx + local_neighbors + 1)

                neighborhood = sorted_e[start:end]
                if len(neighborhood) <= 1:
                    continue

                diff = neighborhood - sorted_e[idx]
                if idx - start >= 0 and idx - start < len(diff):
                    diff[idx - start] = 0.0

                weights = np.exp(-(diff ** 2) / sigma)
                sorted_force[idx] = self.coupling * np.sum(weights * diff)

            coupling_force[order, d] = sorted_force

        # Inertia / Trägheit des Feldes
        self.velocity = 0.92 * self.velocity

        self.velocity += force + coupling_force
        self.velocity += np.random.randn(self.N, self.D) * self.noise

        self.energy += self.velocity

        self.energy = np.clip(self.energy, -3, 3)

# --------------------------------------------------
# Clusterbildung
# --------------------------------------------------

class ClusterDetector:

    def __init__(self):

        self.tick_seq = 0
        self.last_clusters = []
        self.eps = float(getattr(Config, "MCM_CLUSTER_EPS", 0.4) or 0.4)
        self.min_samples = max(2, int(getattr(Config, "MCM_CLUSTER_MIN_SAMPLES", 4) or 4))
        self.detect_every_n = max(1, int(getattr(Config, "MCM_CLUSTER_EVERY_N_TICKS", 2) or 2))

    def detect(self, energy, force: bool = False):

        self.tick_seq = int(self.tick_seq or 0) + 1

        if (not bool(force)) and self.last_clusters and (self.tick_seq % self.detect_every_n) != 0:
            return [np.array(item, copy=True) for item in list(self.last_clusters or [])]

        points = np.asarray(energy, dtype=float)

        if len(points) < self.min_samples:
            self.last_clusters = []
            return []

        db = DBSCAN(eps=self.eps, min_samples=self.min_samples).fit(points)

        labels = db.labels_

        clusters = []

        for c in set(labels):
            if c == -1:
                continue
            clusters.append(np.array(points[labels == c], copy=True))

        self.last_clusters = [np.array(item, copy=True) for item in list(clusters or [])]
        return [np.array(item, copy=True) for item in list(self.last_clusters or [])]


# --------------------------------------------------
# Gedächtnis
# --------------------------------------------------

class Memory:

    def __init__(self):
        self.memory = []
        self.decay = 0.85
        self.max_items = 12

    def store(self, clusters):

        updated_memory = []

        for item in self.memory:
            updated_memory.append({
                "center": float(item["center"]),
                "strength": max(1, int(round(item["strength"] * self.decay)))
            })

        for c in clusters:

            center = float(np.mean(c[:,0]))
            strength = int(len(c))
            merged = False

            for item in updated_memory:
                if abs(item["center"] - center) <= 0.35:
                    item["center"] = 0.5 * (item["center"] + center)
                    item["strength"] += strength
                    merged = True
                    break

            if not merged:
                updated_memory.append({
                    "center": center,
                    "strength": strength
                })

        updated_memory = sorted(
            updated_memory,
            key=lambda x: x["strength"],
            reverse=True
        )[:self.max_items]

        self.memory = updated_memory

    def strongest(self):

        if not self.memory:
            return None

        return max(self.memory, key=lambda x: x["strength"])

    def replay_impulse(self, replay_scale=0.08):

        if not self.memory:
            return 0.0

        item = random.choice(self.memory)

        return replay_scale * float(item["center"])


# --------------------------------------------------
# Attraktoren
# --------------------------------------------------

class AttractorSystem:

    def choose(self, memory, self_state):

        if memory is None:
            if self_state == "stressed":
                return "defense"
            if self_state == "excited":
                return "explore"
            return "neutral"

        e = memory["center"]

        if self_state == "stressed" and e < -0.3:
            return "defense"

        if self_state == "excited" and e >= 1.2:
            return "explore"

        if e < -1.5:
            return "defense"

        if -1.5 <= e < -0.3:
            return "analysis"

        if -0.3 <= e < 1.2:
            return "cooperate"

        if e >= 1.6:
            return "explore"

        return "neutral"

# --------------------------------------------------
# Handlungssystem
# --------------------------------------------------

class ActionSystem:

    def act(self, attractor):

        actions = {
            "defense": "block / withdraw",
            "analysis": "observe / process",
            "cooperate": "engage socially",
            "explore": "seek novelty",
            "neutral": "idle"
        }

        return actions.get(attractor, "idle")


# --------------------------------------------------
# KI Agent
# --------------------------------------------------

class MCM_AI:

    def __init__(self):

        self.perception = Perception()
        self.self_model = SelfModel()
        self.field = MCMField()
        self.cluster = ClusterDetector()
        self.memory = Memory()
        self.attractor = AttractorSystem()
        self.action = ActionSystem()
        self.regulation = RegulationLayer()


    def step(self, stimulus):

        # Wahrnehmung
        external_impulse = self.perception.encode(stimulus)

        # interner Replay-Impuls
        replay_impulse = self.memory.replay_impulse(replay_scale=0.05)
        total_impulse = external_impulse + replay_impulse

        # interne Gedankenzyklen
        internal_cycles = 3

        for _ in range(internal_cycles):
            self.field.step(replay_impulse)

        # Feld Dynamik mit externem Stimulus
        self.field.step(total_impulse)

        # Clusterbildung
        clusters = self.cluster.detect(self.field.energy)

        # Gedächtnis
        self.memory.store(clusters)

        # Selbstzustand
        self_state = self.self_model.evaluate(self.field.energy)

        # Regulation
        self.regulation.regulate(self.field)

        # Attraktor
        attractor = self.attractor.choose(self.memory.strongest(), self_state)

        # Handlung
        action = self.action.act(attractor)

        return action

# --------------------------------------------------
# Regulation / Homeostasis
# --------------------------------------------------

class RegulationLayer:

    def regulate(self, field):

        mean_energy = float(np.mean(field.energy[:,0]))

        # Energie zu hoch → Exploration bremsen
        if mean_energy > 1.6:
            field.velocity *= 0.65
            field.energy[:,0] -= 0.25

        # Energie zu niedrig → Defense bremsen
        if mean_energy < -1.8:
            field.velocity *= 0.7
            field.energy[:,0] += 0.15

        # Energie nahe Gleichgewicht stabilisieren
        if -0.4 < mean_energy < 0.4:
            field.velocity *= 0.95

# --------------------------------------------------
# Beispiel
# --------------------------------------------------
if __name__ == "__main__":

    ai = MCM_AI()

    stimuli = ["neutral", "positive", "negative", "reward", "threat"]

    for t in range(200):

        stimulus = random.choice(stimuli)

        action = ai.step(stimulus)

        mean_energy = np.mean(ai.field.energy[:, 0])

        print(t, stimulus, "→", action, "| energy:", round(mean_energy, 3))