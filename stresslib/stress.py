__author__ = 'aleivag'

import sys
import time

from csv import writer

import argparse
from multiprocessing import Process, Queue


class Generator(Process):
    def __init__(self, manager):
        Process.__init__(self)
        self.manager = manager
        self.queue = manager.manager_queue
        self.small_pool = self.manager.work_finish

    def do_generate(self):
        return []

    def run(self):
        generate_iter = self.do_generate()

        buffer_to_complete = self.manager.p_args.simultaneous
        buffer = []

        while True:
            try:
                work = generate_iter.next()
            except StopIteration:
                break

            buffer.append(work)
            if buffer_to_complete:
                buffer_to_complete -= 1
            else:
                while buffer:
                    self.queue.put(buffer.pop(0))

        for nid in range(self.manager.p_args.simultaneous):
            self.queue.put(None)

class Worker(Process):
    def __init__(self, manager):
        Process.__init__(self)
        self.manager = manager
        self.in_queue = manager.manager_queue
        self.out_queue = manager.work_done_queue

    def do_work(self, work):
        return work

    def run(self):
        while True:
            w = self.in_queue.get()
            if w is None:
                self.out_queue.put(None)
                return

            nw = {'start': time.time()}
            try:
                nw.update(self.do_work(w))
                nw['stop'] = time.time()
                nw['duration'] = nw['stop'] - nw['start']
            except Exception, e:
                nw = {'result': False, 'error': str(e).replace('\n', '-')}
            w.update(nw)
            self.out_queue.put(w)


class Reporter(Process):

    duration = 'duration'

    def __init__(self, manager):
        Process.__init__(self)
        self.manager = manager
        self.out_queue = manager.work_done_queue

    def run(self):
        nones = self.manager.p_args.simultaneous

        results = []
        timeline = {}
        good, bad = 0., 0.
        max_sim  = 0
        ppi_5, ppi_50, ppi_avg, ppi_80, ppi_95 = 0, 0, 0, 0, 0

        while nones:
            q = self.out_queue.get()
            if q is None:
                nones -= 1
                continue

            if q['result']:
                results.append(q['ppi'])
                timeline[q['start']] = timeline.get(q['start'], 0) + 1
                timeline[q['stop']] = timeline.get(q['stop'], 0) - 1
                acum = 0
                for k, v in sorted(timeline.items(), key= lambda x: x[0]):
                    acum += v
                    max_sim = max(acum, max_sim)
                good += 1.
            else:
                bad += 1.


            tdone = good + bad
            pdone = tdone/self.manager.p_args.total*100
            pgood = good/tdone*100

            results.sort()

            if good:
                ppi_5 = results[int(good*0.05)]
                ppi_50 = results[int(good*0.5)]
                ppi_avg = sum(results) / good
                ppi_80 = results[int(good*0.8)]
                ppi_95 = results[int(good*0.95)]


        writer(sys.stdout).writerow(
            [
                self.manager.p_args.name,
                self.manager.p_args.simultaneous,
                self.manager.p_args.total,
                '%.1f%%' % pdone,
                '%.1f%%' % pgood,
                max_sim,
                '%.2f' % ppi_5,
                '%.2f' % ppi_50,
                '%.2f' % ppi_80,
                '%.2f' % ppi_95,
                '%.2f' % ppi_avg
            ]
        )



class Manager(object):

    args = argparse.ArgumentParser(description="Stresser")

    def init_arguments(self):
        self.args.add_argument('--simultaneous', '--sim', default=1, type=int)
        self.args.add_argument('--total', default=10, type=int)
        self.args.add_argument('--name', default="")

    def __init__(self):

        self.init_arguments()

        self.p_args = self.args.parse_args()

        self.work_finish = Queue()
        self.manager_queue = Queue()
        self.work_done_queue = Queue()

    def register_generator(self, generator=Generator):
        self.generator = generator(self)
        return self.generator

    def regirster_workers(self, worker=Worker):
        self.workers = [
            worker(self) for nid in range(self.p_args.simultaneous)
        ]
        return self.workers

    def register_reporter(self, reporter=Reporter):
        self.reporter = reporter(self)

    def start(self):
        self.generator.start()
        map(lambda x: x.start(), self.workers)
        self.reporter.start()
#
        self.generator.join()
        map(lambda x: x.join(), self.workers)
        self.reporter.join()

