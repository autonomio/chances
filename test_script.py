import randomizer

r = randomizer.Randomizer(100, 10)

nums = r.ambience()
nums = r.halton()
nums = r.korobov_matrix()
nums = r.latin_improved()
nums = r.latin_matrix()
nums = r.latin_sudoku()
nums = r.quantum()
nums = r.sobol()
nums = r.uniform_crypto()
nums = r.uniform_mersenne()
randomizer.oned(nums)
randomizer.twod(nums)
randomizer.twod(nums, nums)
