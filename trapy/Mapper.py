class Mapper:
    def __init__(self, initial_seq, max_seq, data_len, window_size, fragment_size):
        self.map = {}
        self.window_size = window_size
        self.fragment_size = fragment_size
        self.mod = max_seq
        self.initial_seq = initial_seq
        self.last = (initial_seq + window_size - 1) % max_seq
        self.n = 0

        # PERROPARCHE
        self.map[0] = 0

        for i in range(initial_seq, initial_seq + window_size):
            if i >= max_seq:
                i = i % max_seq

            self.map[i] = self.n

            self.n += 1

    def get(self, seq):
        # print(("seq-> " + str(seq), "last-> " + str(self.last)))

        if (self.last - seq >= 0 and self.last - seq <= self.fragment_size) or (
            self.last - seq < 0
            and ((self.mod - 1) - seq + self.last) <= self.fragment_size
        ):
            # print("======> moving forward")
            for _ in range(3 * self.window_size):
                self.last = (self.last + 1) % self.mod
                self.map[self.last] = self.n
                # print(str(self.last) + " > " + str(self.map[self.last]))
                self.n += 1
                _ = self.map.pop((self.last - 6 * self.window_size) % self.mod, None)
                # print("removed " + str((self.last - 4 * self.window_size) % self.mod))
            # print("=======> end moving")

        return self.map[seq]


# class Mapper:
#     def __init__(self, initial_seq, max_seq, data_len, step, fragment_size):
#         self.map = {}
#         self.step = step
#         self.mod = max_seq
#         self.first, self.last = initial_seq, (initial_seq - 1) % max_seq
#         self.n = 0

#         for i in range(initial_seq, max_seq):
#             if self.n == data_len + step:
#                 break
#             self.map[i] = self.n
#             self.n += 1

#         for i in range(0, initial_seq):
#             if self.n == data_len + step:
#                 break
#             self.map[i] = self.n
#             self.n += 1

#     def get(self, seq):
#         if seq == self.last:
#             for _ in range(self.step):
#                 self.map[self.first] = self.n
#                 self.n += 1
#                 self.first = (self.first + 1) % self.mod
#                 self.last = (self.last + 1) % self.mod
#         try:
#             return self.map[seq]
#         except KeyError:
#             print(seq)
