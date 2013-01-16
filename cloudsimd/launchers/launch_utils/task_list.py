from __future__ import print_function
import unittest
import time
from launch_utils.sshclient import SshClientException


class SshRetryException(Exception):
    pass



def get_ssh_cmd_generator(ssh_client, cmd, expected_output, max_retries = 100):
    
    print("generator ssh cmd: %s, expected output: %s" % (cmd, expected_output) )
    count = max_retries
    done = False
    
    while not done:
        count -= 1
        
        try:
            result = ssh_client.cmd(cmd)
            if result.strip() == expected_output:
                print("   FOUND %s (%s/%s)" % (cmd, max_retries-count, max_retries))
                yield True
                done = True
        except SshClientException:
            yield False
                    
        if count == 0:
            raise SshRetryException("%s: %s" % (ssh_client.user, cmd))
            yield False
            done = True
        else:
            print("   RETRY %s (%s/%s)" % (cmd,max_retries-count, max_retries))
            yield False

def empty_ssh_queue(generator_list, sleep):
    while len(generator_list):
        time.sleep(sleep)
        for g in generator_list:
            found = g.next()
            if found:
                generator_list.remove(g)
            
                


class TaskCase(unittest.TestCase):

    def test_a_new_task(self):
        print("new")
        
        done = False
        g = get_ssh_cmd_generator("test_cmd", "no", 1)
        while not done:
            done = g.next()
            print (done)
        
        #for found in get_ssh_cmd_generator("yes", "no", 1):
        #print (found)
        
        print("done")

    def test_generator_list(self):
        
        print("\ntest_generator_list\n")
        generator_list = []
        
        print("Adding generators")
        for i in range(3,5):
            g = get_ssh_cmd_generator("yes_%s" % i, "yes", i)
            generator_list.append(g)
            
        
          
        print("Emptying the queue")
        empty_ssh_queue(generator_list)
        print ("test_generator_list done")

if __name__ == "__main__":
    unittest.main()        