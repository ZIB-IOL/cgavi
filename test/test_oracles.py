import random
import unittest
import cupy as cp

from src.auxiliary_functions.auxiliary_functions import fd
from src.oracles.accelerated_gradient_descent import AcceleratedGradientDescent
from src.oracles.conditional_gradients import FrankWolfe
from src.oracles.feasibility_regions import L1Ball, L2Ball
from src.oracles.objective_functions import L2Loss
from src.gpu.memory_allocation import set_gpu_memory

from global_ import gpu_memory_


class TestL1Ball(unittest.TestCase):
    def setUp(self):
        set_gpu_memory(gpu_memory_)
        self.feasiblityRegion = L1Ball(5, 2)

    def test_initial_vertex(self):
        """Tests whether L1Ball.initial_vertex() behaves as intended."""
        inital_vertex = self.feasiblityRegion.initial_vertex()
        self.assertTrue((inital_vertex == cp.array([2, 0, 0, 0, 0])).all(), "Initial vertex is not correctly created.")

    def test_away_oracle(self):
        """Tests whether L1Ball.away_oracle() behaves as intended."""
        active_vertices = cp.array([[1, 0], [0.8, 0.811], [0.8, 0], [0.7, 0], [0.6, 0]])
        direction = cp.array([0, 1, 0, 0, 0])
        away_vertex, active_vertices_idx = self.feasiblityRegion.away_oracle(active_vertices, direction)
        self.assertTrue((away_vertex == cp.array([0, 0.811, 0, 0, 0])).all(), "Wrong away_vertex returned.")
        self.assertTrue(active_vertices_idx == 1, "Wrong active_vertices_index returned.")

    def test_linear_minimization_oracle(self):
        """Tests whether L1Ball.linear_minimization_oracle() behaves as intended."""
        direction = cp.array([0, 1, 0, 0, 0])
        x = cp.array([0.1, 0.2, 0.3, 0.4, 0.5])
        fw_vertex, non_zero_idx, sign, fw_gap = self.feasiblityRegion.linear_minimization_oracle(x, direction)
        self.assertTrue((fw_vertex == cp.array([0, -2, 0, 0, 0])).all(), "Wrong fw_vertex returned.")
        self.assertTrue(sign == -1, "Wrong sign returned.")
        self.assertTrue(non_zero_idx == 1, "Wrong non_zero_idx returned.")
        self.assertTrue(fw_gap == 2.2, "Wrong fw_gap computed.")
        self.assertTrue(fw_vertex.T.dot(direction) <= 0, "<fw_vertex, direction> has to be nonnegative.")

    def test_vertex_among_active_vertices(self):
        """Tests whether L1Ball.vertex_among_active_vertices() behaves as intended."""
        matrix = cp.array([[1, -1, 0],
                           [0, 0, 1]])
        vector = cp.array([[0], [-2]])
        self.assertTrue(self.feasiblityRegion.vertex_among_active_vertices(matrix, vector) is None,
                        "Did not recognize that vertex is not active yet.")
        vector = cp.array([[-1], [0]])
        self.assertTrue(self.feasiblityRegion.vertex_among_active_vertices(matrix, vector) == 1,
                        "Wrong index returned.")
        vector = cp.array([[0], [1]])
        self.assertTrue(self.feasiblityRegion.vertex_among_active_vertices(matrix, vector) == 2,
                        "Wrong index returned.")
        matrix = cp.array([[1]])
        vector = cp.array([[1]])
        self.assertTrue(self.feasiblityRegion.vertex_among_active_vertices(matrix, vector) == 0,
                        "Wrong index returned.")


class TestL2Ball(unittest.TestCase):
    def setUp(self):
        set_gpu_memory(gpu_memory_)
        self.feasiblityRegion = L2Ball(5, 2)

    def test_initial_vertex(self):
        """Tests whether L2Ball.initial_vertex() behaves as intended."""
        inital_vertex = self.feasiblityRegion.initial_vertex()
        self.assertTrue((inital_vertex == cp.array([2, 0, 0, 0, 0])).all(), "Initial vertex is not correctly created.")

    def test_linear_minimization_oracle(self):
        """Tests whether L2Ball.linear_minimization_oracle() behaves as intended."""
        direction = cp.array([0, 1, 0, 0, 0])
        x = cp.array([1, 0, 0, 0, 0])
        fw_vertex, fw_gap = self.feasiblityRegion.linear_minimization_oracle(x, direction)
        self.assertTrue((fw_vertex == cp.array([0, -2, 0, 0, 0])).all(), "Wrong fw_vertex returned.")
        self.assertTrue(fw_gap == 2.0, "Wrong fw_gap computed.")
        self.assertTrue(fw_vertex.T.dot(direction) <= 0, "<fw_vertex, direction> has to be nonnegative.")


class TestL2Loss(unittest.TestCase):

    def setUp(self):
        set_gpu_memory(gpu_memory_)

    def test_evaluate_loss(self):
        """Tests whether L2Loss.evaluate_loss() behaves as intended."""
        for m in range(1, 5):
            for n in range(1, 10):
                A = cp.random.random((m, n))
                b = cp.random.random((m, 1)).flatten()
                x = cp.random.random((n, 1)).flatten()
                lmbda = float(random.random() * n)
                objective_function = L2Loss(A, b, lmbda=lmbda)
                self.assertTrue(
                    abs(1 / A.shape[0] * cp.linalg.norm(A.dot(fd(x)).flatten() + b) ** 2 + lmbda * cp.linalg.norm(
                        x) ** 2 / 2 - objective_function.evaluate_loss(x)) <= 1e-10, "Wrong loss returned.")

    def test_evaluate_gradient(self):
        """Tests whether L2Loss.evaluate_gradient() behaves as intended."""
        for m in range(1, 5):
            for n in range(1, 10):
                A = cp.random.random((m, n))
                b = cp.random.random((m, 1)).flatten()
                x = cp.random.random((n, 1)).flatten()
                lmbda = float(random.random() * n)
                objective_function = L2Loss(A, b, lmbda=lmbda)
                gradient = 2 / m * (A.T.dot(A).dot(x) + A.T.dot(b) + m / 2 * lmbda * x)
                self.assertTrue(
                    (abs(gradient.flatten() - objective_function.evaluate_gradient(x).flatten()) <= 1e-10).all(),
                    "Wrong gradient returned.")

    def test_L(self):
        """Tests whether L2Loss.L() behaves as intended."""
        data_matrix = cp.random.random((5, 3))
        labels = cp.random.random((5, 1))
        loss = L2Loss(data_matrix=data_matrix, labels=labels, lmbda=1)
        L = loss.L()
        L_computed = 2 / data_matrix.shape[0] * cp.max(cp.linalg.eigh(data_matrix.T.dot(data_matrix))[0]) + 1
        self.assertTrue(abs(float(L - L_computed)) <= 1e-10, "L is wrong.")

    def test_evaluate_step_size(self):
        """Tests whether L2Loss.evaluate_step_size() behaves as intended."""
        for m in range(1, 4):
            for n in range(1, 4):
                A = cp.random.random((m, n))
                b = cp.random.random((m, 1)).flatten()
                x = cp.random.random((n, 1)).flatten()
                lmbda = float(random.random() * 7)
                objective_function = L2Loss(A, b, lmbda=lmbda)
                feasibility_region = L1Ball(n, 5)
                gradient = objective_function.evaluate_gradient(x)
                fw_vertex, _, _, _ = feasibility_region.linear_minimization_oracle(x, gradient)
                direction = fw_vertex - x
                exact = objective_function.evaluate_step_size(x, gradient, direction, step_size_rule="exact")
                ls = objective_function.evaluate_step_size(x, gradient, direction, step_size_rule="line_search",
                                                           iterations_line_search=1000)
                tmp_exact = x + exact * direction
                current_value_exact = objective_function.evaluate_loss(tmp_exact)
                tmp_ls = x + ls * direction
                current_value_ls = objective_function.evaluate_loss(tmp_ls)
                self.assertTrue(abs(ls - exact) <= 1e-3, "Exact and line search provide different results.")
                self.assertTrue(abs(
                    current_value_ls - current_value_exact) <= 1e-4, "Exact and line search provide different results.")


class TestFrankWolfe(unittest.TestCase):

    def setUp(self):
        set_gpu_memory(gpu_memory_)

    def test_pairwise_frank_wolfe(self):
        """Tests whether FrankWolfe behaves as intended."""
        for i in range(5):
            m = random.randint(1, 1000)
            n = random.randint(1, 1000)
            radius = random.random() * 100 + 1
            psi = random.random() + 1e-10
            eps = random.random() + 1e-10
            A = cp.random.random((m, n))
            b = cp.random.random((m, 1))
            lmbda = random.random() * 10
            objective = L2Loss(A, b, lmbda)
            region = L1Ball(n, radius)
            oracle = FrankWolfe(objective_function=objective, feasibility_region=region, psi=psi, eps=eps,
                                max_iterations=1000)
            iterate, loss_list, fw_gaps = oracle.optimize()
            self.assertTrue((len(iterate) == n), "Error.")

    def test_vanilla_frank_wolfe(self):
        """Tests whether FrankWolfe behaves as intended."""
        for i in range(0, 5):
            m = random.randint(1, 1000)
            n = random.randint(1, 1000)
            radius = random.random() * 100 + 1
            psi = random.random() + 1e-10
            eps = random.random() + 1e-10
            A = cp.random.random((m, n))
            b = cp.random.random((m, 1))
            lmbda = random.random() * 10
            objective = L2Loss(A, b, lmbda)
            region = L2Ball(n, radius)
            oracle = FrankWolfe(objective_function=objective, feasibility_region=region, psi=psi, eps=eps,
                                max_iterations=1000)
            iterate, loss_list, fw_gaps = oracle.optimize()
            self.assertTrue((len(iterate) == n), "Error.")

    def test_accelerated_gradient_descent(self):
        """Tests whether AcceleratedGradientDescent behaves as intended."""
        for i in range(5):
            m = random.randint(1, 1000)
            n = random.randint(1, 1000)
            A = cp.random.random((m, n))
            b = cp.random.random((m, 1))
            lmbda = random.random() * 10
            objective = L2Loss(A, b, lmbda)
            oracle = AcceleratedGradientDescent(objective_function=objective, dimension=n, max_iterations=1000)
            iterate, loss_list, fw_gaps = oracle.optimize()
            self.assertTrue((len(iterate) == n), "Error.")
