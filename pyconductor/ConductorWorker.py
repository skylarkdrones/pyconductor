#
#  Copyright 2017 Netflix, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from __future__ import print_function, absolute_import
import sys
import time
from pyconductor.conductor import WFClientMgr
from threading import Thread
import socket

hostname = socket.gethostname()


class ConductorWorker:
    """
    Main class for implementing Conductor Workers

    A conductor worker is a separate system that executes the various
    tasks that the conductor server queues up for execution. The worker
    can run on the same instance as the server or on a remote instance.

    The worker generally provides a wrapper around some function that
    performs the actual execution of the task. The function that is
    being executed must return a `dict` with the `status`, `output` and
    `log` keys. If these keys are not present, the worker will raise an
    Exception after completion of the task.

    There are two primary modes to running the worker. It can either be
    run in a continous polling mode, or in a one-time consumption mode.

    The continous polling mode is meant to be run as a daemon process.
    This mode is ideal for small lightweight processes that need to be
    run as soon as they are made available. For more details, view the
    start method.

    The one-time consumption mode is a more contained approach to
    executing tasks. It is ideal for heavyweight tasks, workers
    running on low-spec hardware, or any tasks that need to be run on
    schedule. It allows for more control over how the tasks are
    executed. For more details, view the consume method.
    """
    def __init__(self, server_url, thread_count=1, polling_interval=1.0, worker_id=None):
        """
        Parameters
        ----------
        server_url: str
            The url to the server hosting the conductor api.
            Ex: 'http://localhost:8080/api'
        thread_count: int, optional
            The number of threads that will be polling for and
            executing tasks in case of using the start method. By
            default, thread_count is set to 1
        polling_interval: float, optional
            The number of seconds that each worker thread will wait
            between polls to the conductor server. By default,
            polling_interval is set to 1.0
        domain: str, optional
            The domain of the task under which the worker will run. For
            further details refer to the conductor server documentation
            By default, it is set to None
        """
        wfcMgr = WFClientMgr(server_url)
        self.workflowClient = wfcMgr.workflowClient
        self.taskClient = wfcMgr.taskClient
        # Checking that the arguments are valid. Converting thread_count
        # to float as that is a little more lenient. It will be converted
        # to int when it is being used.
        self.thread_count = float(thread_count)
        self.polling_interval = float(polling_interval)
        self.worker_id = worker_id or hostname

    def _execute(self, task, exec_function):
        try:
            resp = exec_function(task)
            if type(resp) is not dict or not all(key in resp for key in ('status', 'output', 'logs')):
                raise Exception('Task execution function MUST return a response as a dict with status, output and logs fields')
            task['status'] = resp['status']
            task['outputData'] = resp['output']
            task['logs'] = resp['logs']
            self.taskClient.updateTask(task)
        except Exception as err:
            print('Error executing task: ' + str(err))
            task['status'] = 'FAILED'
            self.taskClient.updateTask(task)

    def _poll_and_execute(self, taskType, exec_function, domain=None):
        while True:
            time.sleep(float(self.polling_interval))
            polled = self.taskClient.pollForTask(taskType, self.worker_id, domain)
            if polled is not None:
                if self.taskClient.ackTask(polled['taskId'], self.worker_id):
                    self._execute(polled, exec_function)

    def start(self, taskType, exec_function, wait, domain=None):
        """
        start begins the continuous polling of the conductor server

        In cases where the tasks are light weight, or a single worker
        is being run exclusively on an instance, continous polling is
        the preferred method of task execution. It is also the designed
        way of workers being run.

        Parameters
        ----------
        taskType: str
            The name of the task that the worker is looking to execute
        exec_function: function
            The function that the worker will execute. The function
            must return a dict with the `status`, `output` and `logs`
            keys present. If this is not present, an Exception will be
            raised
        wait: bool
            Whether the worker will block execution of further code.
            If multiple workers are being called from the same program,
            all but the last start call but have wait set to False. The
            last start call must have wait set to True. If only a
            single worker is being called, wait must be set to True
        domain: str, optional
            The domain of the task under which the worker will run. For
            further details refer to the conductor server documentation
            By default, it is set to None
        """
        for x in range(0, int(self.thread_count)):
            thread = Thread(target=self._poll_and_execute, args=(taskType, exec_function, domain,))
            thread.daemon = True
            thread.start()
        if wait:
            while 1:
                time.sleep(1)

    def consume(self, taskType, exec_function, domain=None, limit=0, checkExistingTasks=True):
        """
        consume executes `limit` or all of the available tasks

        In cases where a worker is running heavyweight tasks, or is
        running on an instance where resources are limited, consume is
        the ideal mode for workers. It is meant to be used to run
        workers through a scheduler like cron.

        It is useful if certain tasks shouldn't be running in parallel.
        For example, if we are running different resource-heavy tasks
        like image processing and compression on the same instance, it
        is useful to first complete all the image compression tasks and
        then move to the compression tasks. consume allows us to use
        the same instance for various workers.

        Parameters
        ----------
        taskType: str
            The name of the task that the worker is looking to execute
        exec_function: function
            The function that the worker will execute. The function
            must return a dict with the `status`, `output` and `logs`
            keys present. If this is not present, an Exception will be
            raised
        domain: str, optional
            The domain of the task under which the worker will run. For
            further details refer to the conductor server documentation
            By default, it is set to None
        limit: int, optional
            The number of tasks that the worker will consume before
            completion. Can be used to control the total instances of
            the same task running. By default, it is set to 0, in which
            case it completes all the available tasks
        checkExistingTasks: bool, optional
            Flag to check to see whether tasks of the same type are
            already running. If they are, then all running tasks are
            considered as a part of the limit. If the number of
            existing tasks are greater than or equal to the limit, no
            tasks will be run. By default, this is set to True
        """

        # TODO (26 Feb 2019 sam): Create separate consume_sequential and consume_parallel methods
        # TODO (26 Feb 2019 sam): Implement limit and checkExistingTasks functionality
        while True:
            polled = self.taskClient.pollForTask(taskType, self.worker_id, domain)
            if polled is None:
                break
            if self.taskClient.ackTask(polled['taskId'], self.worker_id):
                thread = Thread(target=self._execute, args=(polled, exec_function,))
                thread.start()


def exc(taskType, inputData, startTime, retryCount, status, callbackAfterSeconds, pollCount):
    print('Executing the function')
    return {'status': 'COMPLETED', 'output': {}}


def main():
    cc = ConductorWorker('http://localhost:8080/api', 5, 0.1)
    cc.start(sys.argv[1], exc, False)
    cc.start(sys.argv[2], exc, True)


if __name__ == '__main__':
    main()
